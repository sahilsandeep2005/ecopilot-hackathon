from __future__ import annotations

from typing import Any

from agent.schemas import BuildingState, ControlAction
from control.fallback_controller import safe_fallback_action
from control.safety_shield import SafetyShield
from core.config import settings
from core.storage import SQLiteStore

store = SQLiteStore(settings.db_path)
shield = SafetyShield()


def validate_control_action(action: dict[str, Any]) -> dict[str, Any]:
    """Validate a proposed action and issue a short-lived, action-bound approval token."""
    raw_state = store.latest_state("controlled")
    if raw_state is None:
        return {"approved": False, "reasons": ["No controlled state is available."]}
    try:
        state = BuildingState.model_validate(raw_state)
        parsed_action = ControlAction.model_validate(action)
    except Exception as exc:
        return {"approved": False, "reasons": [f"Schema validation failed: {exc}"]}
    if parsed_action.created_for_step == 0:
        parsed_action.created_for_step = state.sim_step
    result = shield.validate(parsed_action, state, issue_token=True)
    if not result.approved:
        store.log_event(
            "WARNING",
            "safety_shield",
            "Control action rejected.",
            {"action": parsed_action.model_dump(mode="json"), "reasons": result.reasons},
        )
    return result.model_dump(mode="json")


def apply_control_action(action: dict[str, Any], approval_token: str) -> dict[str, Any]:
    """Queue a validated action for the controlled EnergyPlus twin."""
    raw_state = store.latest_state("controlled")
    if raw_state is None:
        return {"ok": False, "error": "No controlled state is available."}
    try:
        state = BuildingState.model_validate(raw_state)
        parsed_action = ControlAction.model_validate(action)
    except Exception as exc:
        return {"ok": False, "error": f"Schema validation failed: {exc}"}

    valid, message = shield.tokens.verify(approval_token, parsed_action, state.sim_step)
    if not valid:
        store.log_event(
            "WARNING",
            "safety_shield",
            "Approval token verification failed.",
            {"action_id": parsed_action.action_id, "reason": message},
        )
        return {"ok": False, "error": message}

    current_validation = shield.validate(parsed_action, state, issue_token=False)
    if not current_validation.approved:
        return {"ok": False, "error": "State changed and the action is no longer safe.", "reasons": current_validation.reasons}

    row = store.insert_action(
        parsed_action.model_dump(mode="json"),
        approval_token=approval_token,
        status="approved",
    )
    store.log_event(
        "INFO",
        "mcp_control",
        f"Queued {parsed_action.mode} action for EnergyPlus.",
        {"action": parsed_action.model_dump(mode="json"), "database_row": row.get("id")},
    )
    return {"ok": True, "queued": True, "action_row": row}


def rollback_last_action(reason: str = "Requested by supervisory recovery logic") -> dict[str, Any]:
    """Queue a safety-approved reset that returns all controlled schedules to baseline."""
    raw_state = store.latest_state("controlled")
    if raw_state is None:
        return {"ok": False, "error": "No controlled state is available."}
    state = BuildingState.model_validate(raw_state)
    action = safe_fallback_action(state, reason)
    if not action.reset_to_baseline:
        action = ControlAction(
            mode="SAFE_FALLBACK",
            reset_to_baseline=True,
            hold_steps=1,
            reason=f"Rollback requested: {reason}",
            confidence=1.0,
            created_for_step=state.sim_step,
            source="recovery_tool",
        )
    validation = shield.validate(action, state, issue_token=True)
    if not validation.approved or not validation.approval_token:
        return {"ok": False, "error": "Rollback action unexpectedly failed validation."}
    return apply_control_action(action.model_dump(mode="json"), validation.approval_token)
