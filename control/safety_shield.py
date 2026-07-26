from __future__ import annotations

import base64
import hashlib
import hmac
import json

from agent.schemas import BuildingState, ControlAction, ValidationResult
from control.constraints import ConstraintChecker
from core.config import settings


class ApprovalTokenManager:
    def __init__(self, secret: str = settings.approval_secret, valid_steps: int = settings.approval_token_valid_steps):
        self.secret = secret.encode("utf-8")
        self.valid_steps = valid_steps

    def issue(self, action: ControlAction, current_step: int) -> tuple[str, int]:
        expires_at = int(current_step) + int(self.valid_steps)
        payload = {
            "action_hash": action.digest(),
            "issued_at_step": int(current_step),
            "expires_at_step": expires_at,
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self.secret, body, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(body).decode().rstrip("=") + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return token, expires_at

    @staticmethod
    def _decode_part(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def verify(self, token: str, action: ControlAction, current_step: int) -> tuple[bool, str]:
        try:
            body_part, signature_part = token.split(".", 1)
            body = self._decode_part(body_part)
            provided_signature = self._decode_part(signature_part)
            expected_signature = hmac.new(self.secret, body, hashlib.sha256).digest()
            if not hmac.compare_digest(provided_signature, expected_signature):
                return False, "Approval token signature is invalid."
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return False, "Approval token is malformed."

        if payload.get("action_hash") != action.digest():
            return False, "The action was modified after validation."
        if int(current_step) > int(payload.get("expires_at_step", -1)):
            return False, "Approval token has expired for the current simulation step."
        return True, "Approval token is valid."


class SafetyShield:
    def __init__(self):
        self.checker = ConstraintChecker()
        self.tokens = ApprovalTokenManager()

    def validate(self, action: ControlAction, state: BuildingState, issue_token: bool = True) -> ValidationResult:
        errors, warnings = self.checker.validate(action, state)
        if errors:
            return ValidationResult(
                approved=False,
                reasons=errors,
                warnings=warnings,
                action=action,
            )
        token = None
        expires_at = None
        if issue_token:
            token, expires_at = self.tokens.issue(action, state.sim_step)
        return ValidationResult(
            approved=True,
            reasons=["All hard comfort, IAQ, actuator, and deadband constraints passed."],
            warnings=warnings,
            approval_token=token,
            expires_at_step=expires_at,
            action=action,
        )
