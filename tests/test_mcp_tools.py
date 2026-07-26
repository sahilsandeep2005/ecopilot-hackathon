from mcp_server.tools.model_tools import inspect_building_model


def test_model_tool_handles_missing_file():
    result = inspect_building_model("definitely-missing.idf")
    assert result["ok"] is False
