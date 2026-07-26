from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from core.config import settings
from mcp_server.tools.control_tools import (
    apply_control_action,
    rollback_last_action,
    validate_control_action,
)
from mcp_server.tools.model_tools import discover_exchange_points, inspect_building_model
from mcp_server.tools.optimizer_tools import optimize_control_action
from mcp_server.tools.recovery_tools import generate_final_report, read_runtime_messages
from mcp_server.tools.state_tools import (
    compare_with_baseline,
    get_live_building_state,
    get_recent_history,
)

mcp = FastMCP(
    "EcoPilot EnergyPlus Control",
    instructions=(
        "Tools for inspecting EnergyPlus, reading live building states, optimizing safe actions, "
        "validating actions, applying approved controls, and recovering to baseline."
    ),
    stateless_http=True,
    json_response=True,
)
mcp.settings.host = settings.mcp_host
mcp.settings.port = settings.mcp_port


@mcp.tool()
def inspect_building_model_tool(idf_path: str = "") -> dict:
    """Inspect the controlled IDF model or a supplied IDF path."""
    return inspect_building_model(idf_path or None)


@mcp.tool()
def discover_exchange_points_tool(filter_text: str = "", limit: int = 250) -> dict:
    """Discover live EnergyPlus sensors, meters, and actuators."""
    return discover_exchange_points(filter_text, limit)


@mcp.tool()
def get_live_building_state_tool(mode: str = "controlled") -> dict:
    """Read the latest baseline or controlled EnergyPlus state."""
    return get_live_building_state(mode)


@mcp.tool()
def get_recent_history_tool(mode: str = "controlled", limit: int = 12) -> dict:
    """Read a compact recent state history for trend analysis."""
    return get_recent_history(mode, limit)


@mcp.tool()
def compare_with_baseline_tool() -> dict:
    """Compare cumulative energy and peak demand of the digital twins."""
    return compare_with_baseline()


@mcp.tool()
def optimize_control_action_tool() -> dict:
    """Generate ranked candidate actions using deterministic optimization."""
    return optimize_control_action()


@mcp.tool()
def validate_control_action_tool(action: dict) -> dict:
    """Validate a candidate action and issue an approval token."""
    return validate_control_action(action)


@mcp.tool()
def apply_control_action_tool(action: dict, approval_token: str) -> dict:
    """Queue an action only when its safety token is valid."""
    return apply_control_action(action, approval_token)


@mcp.tool()
def rollback_last_action_tool(reason: str = "Supervisory recovery requested") -> dict:
    """Restore baseline schedule control through a validated reset action."""
    return rollback_last_action(reason)


@mcp.tool()
def read_runtime_messages_tool(limit: int = 30, severity: str = "") -> dict:
    """Read recent runtime warnings, errors, and control events."""
    return read_runtime_messages(limit, severity)


@mcp.tool()
def generate_final_report_tool() -> dict:
    """Calculate final evaluation metrics from the two simulation runs."""
    return generate_final_report()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
