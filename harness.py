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


def _extract_text(resp) -> str:
    if isinstance(resp, str):
        return resp
    for attr in ("text", "output", "content"):
        v = getattr(resp, attr, None)
        if isinstance(v, str):
            return v
    return str(resp)
