"""A complete, model-agnostic agent loop over an external computer.

This is the reference for "bring your own harness": a real tool-calling loop that
uses `tools.py`. Plug in any chat model that supports OpenAI-style tool calls —
the loop screenshots/execs/clicks on the computer until the model stops calling
tools.

    ORGO_API_KEY=sk_live_... OPENAI_API_KEY=sk-... \
        python agent_loop.py "open a terminal and print the kernel version"

Swap `OpenAIClient` for your own provider; the loop only needs `.chat(messages,
tools) -> (text, tool_calls)`.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Protocol

from external_compute import ExternalComputer, OrgoProvider
from tools import TOOL_SCHEMAS, dispatch


class ChatModel(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> tuple[str, list[dict]]:
        """Return (assistant_text, tool_calls). Each tool call: {id, name, arguments}."""
        ...


class OpenAIClient:
    """Thin OpenAI adapter. Requires `pip install openai` and OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI

        self._c = OpenAI()
        self._model = model

    def chat(self, messages, tools):
        resp = self._c.chat.completions.create(model=self._model, messages=messages, tools=tools)
        msg = resp.choices[0].message
        calls = [
            {"id": tc.id, "name": tc.function.name, "arguments": json.loads(tc.function.arguments or "{}")}
            for tc in (msg.tool_calls or [])
        ]
        return msg.content or "", calls


def run_agent(computer: ExternalComputer, goal: str, model: ChatModel, *, max_steps: int = 12) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You control a Linux computer via tools. Work step by step; stop when the goal is met."},
        {"role": "user", "content": goal},
    ]
    final = ""
    for _ in range(max_steps):
        text, calls = model.chat(messages, TOOL_SCHEMAS)
        if text:
            final = text
        if not calls:
            break
        messages.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in calls
        ]})
        for call in calls:
            result = dispatch(computer, call["name"], call["arguments"])
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)[:4000]})
    return final


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python agent_loop.py '<goal>'")
        return 2
    goal = sys.argv[1]
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY (or swap OpenAIClient for your own ChatModel).")
        return 1

    provider = OrgoProvider()
    computer = provider.create(name="agent-loop")
    try:
        print(run_agent(computer, goal, OpenAIClient()))
    finally:
        computer.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
