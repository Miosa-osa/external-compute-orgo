"""Orchestration harnesses — the part that *decides* what to run on the box.

The whole point of the normalized ``ExternalComputer`` interface is that the
orchestrator does not care which vendor is underneath. The same harness drives a
MIOSA cloud computer, an Orgo box, or a BYOC host.

This file shows four harness shapes, matching "all of the above + custom":

    1. ProbeHarness     — deterministic, no LLM. Proves the wiring end-to-end.
    2. MiosaModelHarness— drives the box with MIOSA's hosted model (completions API).
    3. OptimalHarness   — hands the box to MIOSA's Optimal agent (sketch).
    4. your own         — implement run(computer) however you like.

A harness only depends on ``ExternalComputer``. That's the contract.
"""

from __future__ import annotations

import abc
import os
from typing import Optional

from external_compute import ExternalComputer


class Harness(abc.ABC):
    """Anything that can drive a normalized computer toward a goal."""

    @abc.abstractmethod
    def run(self, computer: ExternalComputer, goal: str) -> str: ...


class ProbeHarness(Harness):
    """No LLM. Runs a fixed sequence to verify the box is drivable."""

    def run(self, computer: ExternalComputer, goal: str) -> str:
        info = computer.info
        lines = [f"[{info.provider}] {info.name} ({info.id}) status={info.status}"]
        for cmd in ("whoami", "uname -sm", "nproc", "free -m | awk 'NR==2{print $2\"MB\"}'"):
            r = computer.exec(cmd)
            lines.append(f"  $ {cmd!r:32} -> {r.output.strip()!r} (exit {r.exit_code})")
        # Prove the shell endpoint is discoverable (the "SSH path").
        ep = computer.shell_endpoint()
        lines.append(f"  shell: kind={ep.kind} uri={ep.uri[:60]}...")
        return "\n".join(lines)


class MiosaModelHarness(Harness):
    """Drive the box with MIOSA's hosted model via the completions API.

    The model proposes shell commands; we execute them on whatever computer was
    handed in. A real loop would feed exec output back to the model until done —
    kept to a single step here so the example stays readable.
    """

    def __init__(self, model: str = "miosa-coder", api_key: Optional[str] = None) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("MIOSA_API_KEY")

    def run(self, computer: ExternalComputer, goal: str) -> str:
        from miosa import Miosa  # optional dep

        client = Miosa(api_key=self._api_key)
        prompt = (
            "You drive a Linux computer by emitting ONE shell command. "
            f"Goal: {goal}. Reply with only the command.\n"
        )
        resp = client.completions.create(model=self._model, prompt=prompt)
        command = _extract_text(resp).strip().splitlines()[0]
        result = computer.exec(command)
        return f"model->{command!r}\nresult-> exit {result.exit_code}: {result.output.strip()}"


class OptimalHarness(Harness):
    """Hand the box to MIOSA's Optimal agent (the canonical platform agent).

    Optimal already speaks the MIOSA computer surface, so we expose the external
    box to it through the same normalized handle. This is a sketch of the wiring;
    the real Optimal session API lives in the platform.
    """

    def run(self, computer: ExternalComputer, goal: str) -> str:
        # Pseudocode — replace with the real Optimal session client.
        # session = optimal.sessions.create(resource_type="external_computer",
        #                                    exec=computer.exec,
        #                                    shell=computer.shell_endpoint())
        # return session.run(goal)
        return (
            f"[OptimalHarness] would bind Optimal to {computer.info.provider}:{computer.info.id} "
            f"via exec()+shell_endpoint() and pursue: {goal}"
        )


class ClaudeComputerUseHarness(Harness):
    """Drive the box with Anthropic's Claude Computer Use loop.

    Same agent loop you'd run against any computer: screenshot -> Claude with the
    computer tool -> execute the returned actions -> repeat. The only thing that
    changes vs a native MIOSA computer is nothing — the actions land on the
    ExternalComputer, which forwards them to Orgo.

    Needs: pip install anthropic, and ANTHROPIC_API_KEY.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", width: int = 1280, height: int = 720, max_iters: int = 12) -> None:
        self._model = model
        self._w, self._h = width, height
        self._max_iters = max_iters

    def run(self, computer: ExternalComputer, goal: str) -> str:
        import base64

        import anthropic

        client = anthropic.Anthropic()
        tools = [{"type": "computer_20250124", "name": "computer", "display_width_px": self._w, "display_height_px": self._h}]
        messages = [{"role": "user", "content": goal}]

        transcript: list[str] = []
        for _ in range(self._max_iters):
            resp = client.beta.messages.create(model=self._model, max_tokens=4096, tools=tools, messages=messages, betas=["computer-use-2025-01-24"])
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    transcript.append(block.text)
                elif getattr(block, "type", None) == "tool_use":
                    out = self._act(computer, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            if not tool_results:
                break
            messages.append({"role": "user", "content": tool_results})
        return "\n".join(transcript) or "(no text output)"

    def _act(self, computer: ExternalComputer, inp: dict):
        import base64

        action = inp.get("action")
        if action == "screenshot":
            img = base64.b64encode(computer.screenshot()).decode()
            return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}}]
        if action in ("left_click", "right_click", "double_click"):
            x, y = inp["coordinate"]
            getattr(computer, action, computer.left_click)(int(x), int(y))
            return [{"type": "text", "text": "ok"}]
        if action == "type":
            computer.type(inp["text"])
            return [{"type": "text", "text": "ok"}]
        if action == "key":
            computer.key(inp["text"])
            return [{"type": "text", "text": "ok"}]
        return [{"type": "text", "text": f"unsupported action {action}"}]


def _extract_text(resp) -> str:
    if isinstance(resp, str):
        return resp
    for attr in ("text", "output", "content"):
        v = getattr(resp, attr, None)
        if isinstance(v, str):
            return v
    return str(resp)
