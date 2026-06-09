"""Tools for controlling an external computer from YOUR OWN agent / harness.

If you're building your own harness — your platform, your agent, your model — you
don't want our orchestration loop, you want the raw controls. This module gives
them to you as standard tool/function-calling schemas plus a dispatcher, so you
can drop external-computer control straight into an OpenAI / Anthropic / custom
agent loop.

    from external_compute import OrgoProvider
    from tools import TOOL_SCHEMAS, dispatch

    computer = OrgoProvider().create(name="agent-box")

    # 1. Advertise the tools to your model (OpenAI-style here):
    response = your_llm.create(model=..., tools=TOOL_SCHEMAS, messages=[...])

    # 2. When the model calls a tool, run it on the computer:
    for call in response.tool_calls:
        result = dispatch(computer, call.name, call.arguments)
        # feed `result` back to your model and loop

The schemas are plain dicts (JSON Schema), so they work with any provider's
tool-calling format — adapt the envelope, keep the function definitions.
"""

from __future__ import annotations

import base64
from typing import Any

from external_compute import ExternalComputer

# OpenAI-style function tool schemas. For Anthropic, map name/description/
# parameters -> name/description/input_schema. The function set is the contract.
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Run a shell command on the computer and return stdout/stderr and exit code.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Capture the current screen. Returns a base64-encoded PNG.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "left_click",
            "description": "Click the mouse at pixel coordinates (origin top-left).",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type",
            "description": "Type text at the current focus.",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "key",
            "description": "Press a key or chord, e.g. 'Enter', 'ctrl+c'.",
            "parameters": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file path on the computer.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the computer.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
]


def dispatch(computer: ExternalComputer, name: str, args: dict[str, Any]) -> Any:
    """Execute one tool call against the computer; return a JSON-serializable result."""
    if name == "exec":
        r = computer.exec(args["command"], timeout=args.get("timeout"))
        return {"output": r.output, "exit_code": r.exit_code, "error": r.error}
    if name == "screenshot":
        return {"image_base64": base64.b64encode(computer.screenshot()).decode()}
    if name == "left_click":
        computer.left_click(int(args["x"]), int(args["y"]))
        return {"ok": True}
    if name == "type":
        computer.type(args["text"])
        return {"ok": True}
    if name == "key":
        computer.key(args["key"])
        return {"ok": True}
    if name == "write_file":
        computer.write_file(args["path"], args["content"])
        return {"ok": True}
    if name == "read_file":
        return {"content": computer.read_file(args["path"])}
    raise ValueError(f"unknown tool: {name}")


# Convenience: Anthropic-format schemas (input_schema instead of parameters).
def anthropic_tools() -> list[dict]:
    return [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in TOOL_SCHEMAS
    ]
