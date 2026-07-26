from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from agent.memory import AgentMemory
from agent.prompts import SYSTEM_PROMPT, cycle_prompt
from core.config import settings


class EcoPilotAgent:
    def __init__(self, deterministic_only: bool = False):
        self.deterministic_only = deterministic_only
        self.memory = AgentMemory()
        self.ollama_client = None
        if not deterministic_only:
            try:
                from ollama import Client

                self.ollama_client = Client(host=settings.ollama_host)
            except Exception as exc:
                self.memory.record_error(f"Ollama client could not be initialized: {exc}")
                self.deterministic_only = True

    @staticmethod
    def _tool_schema(tool: Any) -> dict[str, Any]:
        input_schema = getattr(tool, "inputSchema", None)
        if input_schema is None:
            dumped = tool.model_dump(by_alias=True) if hasattr(tool, "model_dump") else {}
            input_schema = dumped.get("inputSchema", {"type": "object", "properties": {}})
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": input_schema,
            },
        }

    @staticmethod
    def _extract_tool_result(result: Any) -> Any:
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured
        texts: list[str] = []
        for content in getattr(result, "content", []) or []:
            text = getattr(content, "text", None)
            if text is not None:
                texts.append(text)
        joined = "\n".join(texts)
        if joined:
            try:
                return json.loads(joined)
            except json.JSONDecodeError:
                return joined
        return {"ok": not bool(getattr(result, "isError", False))}

    @staticmethod
    def _tool_name(tools: list[Any], prefix: str) -> str:
        for tool in tools:
            if tool.name == prefix or tool.name.startswith(prefix):
                return tool.name
        raise KeyError(f"Required MCP tool not found: {prefix}")

    async def _call(self, session: ClientSession, name: str, arguments: dict | None = None) -> Any:
        result = await session.call_tool(name, arguments=arguments or {})
        value = self._extract_tool_result(result)
        self.memory.record_cycle(f"MCP tool called: {name}", {"result": value})
        return value

    async def deterministic_cycle(self, session: ClientSession, tools: list[Any]) -> dict[str, Any]:
        state_tool = self._tool_name(tools, "get_live_building_state")
        optimize_tool = self._tool_name(tools, "optimize_control_action")
        validate_tool = self._tool_name(tools, "validate_control_action")
        apply_tool = self._tool_name(tools, "apply_control_action")

        state_result = await self._call(session, state_tool, {"mode": "controlled"})
        if not isinstance(state_result, dict) or not state_result.get("ok"):
            return {"ok": False, "error": "Controlled state is not ready."}
        optimization = await self._call(session, optimize_tool)
        if not isinstance(optimization, dict) or not optimization.get("ok"):
            return {"ok": False, "error": "Optimizer did not produce an action.", "details": optimization}
        action = optimization.get("selected_action")
        validation = await self._call(session, validate_tool, {"action": action})
        if not isinstance(validation, dict) or not validation.get("approved"):
            return {"ok": False, "error": "Optimizer action failed safety validation.", "details": validation}
        applied = await self._call(
            session,
            apply_tool,
            {"action": action, "approval_token": validation["approval_token"]},
        )
        return {"ok": bool(isinstance(applied, dict) and applied.get("ok")), "action": action, "applied": applied}

    async def llm_cycle(self, session: ClientSession, tools: list[Any]) -> dict[str, Any]:
        if self.ollama_client is None:
            return await self.deterministic_cycle(session, tools)

        schemas = [self._tool_schema(tool) for tool in tools]
        messages: list[Any] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": cycle_prompt()},
        ]
        called_names: list[str] = []
        final_content = ""

        for _ in range(settings.agent_max_tool_rounds):
            kwargs = {
                "model": settings.ollama_model,
                "messages": messages,
                "tools": schemas,
                "stream": False,
            }
            try:
                response = await asyncio.to_thread(
                    self.ollama_client.chat,
                    **kwargs,
                    think=settings.ollama_think,
                )
            except TypeError:
                response = await asyncio.to_thread(self.ollama_client.chat, **kwargs)

            assistant_message = response.message
            messages.append(assistant_message)
            final_content = getattr(assistant_message, "content", "") or ""
            tool_calls = getattr(assistant_message, "tool_calls", None) or []
            if not tool_calls:
                break

            for tool_call in tool_calls:
                name = tool_call.function.name
                arguments = tool_call.function.arguments or {}
                called_names.append(name)
                try:
                    result = await self._call(session, name, arguments)
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                    self.memory.record_error(f"Tool call failed: {name}: {exc}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(result, default=str),
                    }
                )

        applied_by_llm = any(name.startswith("apply_control_action") for name in called_names)
        if not applied_by_llm:
            fallback = await self.deterministic_cycle(session, tools)
            self.memory.record_cycle(
                "LLM did not complete safe actuation; deterministic supervisory fallback executed.",
                {"called_tools": called_names, "fallback": fallback},
            )
            return {
                "ok": fallback.get("ok", False),
                "llm_summary": final_content,
                "called_tools": called_names,
                "fallback": fallback,
            }

        return {
            "ok": True,
            "llm_summary": final_content,
            "called_tools": called_names,
        }

    async def run_once(self) -> dict[str, Any]:
        async with streamable_http_client(settings.mcp_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_response = await session.list_tools()
                tools = list(tool_response.tools)
                if self.deterministic_only:
                    result = await self.deterministic_cycle(session, tools)
                else:
                    result = await self.llm_cycle(session, tools)
                self.memory.record_cycle("Supervisory cycle finished.", result)
                return result


async def main_async(args: argparse.Namespace) -> int:
    agent = EcoPilotAgent(deterministic_only=args.deterministic)
    if args.once:
        result = await agent.run_once()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1

    while True:
        try:
            result = await agent.run_once()
            print(json.dumps(result, default=str))
        except (KeyboardInterrupt, asyncio.CancelledError):
            return 0
        except Exception as exc:
            agent.memory.record_error(f"Supervisory cycle failed: {exc}")
            print(f"Agent cycle error: {exc}", file=sys.stderr)
        await asyncio.sleep(settings.agent_interval_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the EcoPilot MCP/Ollama supervisory agent.")
    parser.add_argument("--once", action="store_true", help="Run exactly one supervisory cycle.")
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Use the optimizer and MCP tools without Ollama. Useful for integration testing.",
    )
    return parser


def main() -> int:
    return asyncio.run(main_async(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
