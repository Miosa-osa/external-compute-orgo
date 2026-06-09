"""Normalized external-compute interface.

MIOSA already exposes three compute substrates behind one API:

    1. miosa-cloud      — Firecracker microVMs on MIOSA's fleet
    2. opencomputers    — the user's own hardware over an outbound WebSocket (BYOC)
    3. external          — a third-party provider; this repo implements Orgo  ← this module

The point of this file is the *contract*. Any external provider that can
satisfy ``ComputeProvider`` + ``ExternalComputer`` becomes a drop-in compute
source that MIOSA's agent (Optimal / OSA / a hosted model) — or a customer's
own harness — can drive without knowing or caring which vendor is underneath.

The surface deliberately mirrors ``miosa.resources.computer.Computer`` so that
orchestration code written against a MIOSA computer works unchanged against an
external one. See README.md for the mapping table.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExecResult:
    """Result of a shell/command execution. Mirrors miosa ExecResult."""

    output: str
    exit_code: int
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class ShellEndpoint:
    """How to open an interactive shell / PTY on the box.

    This is the "orchestrate via SSH" handle. Different providers expose it
    differently:

    - miosa-cloud : real SSH or the envd exec channel
    - orgo        : a WebSocket terminal (wss://.../ws/terminal?token=...)
                    — there is no port 22, so ``kind`` tells the harness which
                    transport to speak.

    A custom harness inspects ``kind`` and connects accordingly; a harness that
    only needs one-shot commands ignores this and calls ``computer.exec()``.
    """

    kind: str  # "ssh" | "websocket" | "exec-only"
    uri: str  # ssh://user@host:port  OR  wss://.../ws/terminal?token=...
    token: Optional[str] = None
    meta: dict = field(default_factory=dict)


@dataclass
class ComputerInfo:
    """Provider-neutral description of a running box."""

    id: str
    name: str
    provider: str  # "orgo", "miosa-cloud", ...
    status: str  # "running" | "stopped" | ...
    # Best-effort connection details, may be empty for some providers.
    public_url: Optional[str] = None
    raw: dict = field(default_factory=dict)


class ExternalComputer(abc.ABC):
    """A single running machine, normalized to MIOSA's Computer surface.

    Only the methods MIOSA's orchestration actually depends on are required.
    Optional capabilities (computer-use clicks, file I/O, port ingress) raise
    ``NotImplementedError`` when a provider can't back them, so a harness can
    feature-detect rather than guess.
    """

    # ── identity ──────────────────────────────────────────────────────────
    @property
    @abc.abstractmethod
    def info(self) -> ComputerInfo: ...

    # ── orchestration core (the "SSH path") ───────────────────────────────
    @abc.abstractmethod
    def exec(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        """Run a shell command and return output + exit code."""

    @abc.abstractmethod
    def shell_endpoint(self) -> ShellEndpoint:
        """Return how to open an interactive shell (for streaming harnesses)."""

    # ── computer-use (optional) ───────────────────────────────────────────
    def screenshot(self) -> bytes:
        raise NotImplementedError("provider does not support screenshots")

    def left_click(self, x: int, y: int) -> None:
        raise NotImplementedError("provider does not support clicks")

    def type(self, text: str) -> None:
        raise NotImplementedError("provider does not support typing")

    def key(self, key: str) -> None:
        raise NotImplementedError("provider does not support key events")

    # ── files (optional) ──────────────────────────────────────────────────
    def write_file(self, path: str, content: str) -> None:
        raise NotImplementedError("provider does not support file write")

    def read_file(self, path: str) -> str:
        raise NotImplementedError("provider does not support file read")

    # ── port ingress (optional) ───────────────────────────────────────────
    def preview_url(self, port: int, path: str = "/") -> str:
        """Public URL for a service on ``port`` inside the box.

        Many external providers cannot expose arbitrary ports. When they can't,
        this raises and MIOSA's edge tunnel is used instead (see README).
        """
        raise NotImplementedError("provider does not support port ingress")

    # ── lifecycle ─────────────────────────────────────────────────────────
    @abc.abstractmethod
    def stop(self) -> None: ...

    @abc.abstractmethod
    def destroy(self) -> None: ...


class ComputeProvider(abc.ABC):
    """A source of external computers (one per third-party vendor)."""

    name: str

    @abc.abstractmethod
    def create(self, *, name: str, **opts) -> ExternalComputer: ...

    @abc.abstractmethod
    def get(self, computer_id: str) -> ExternalComputer: ...

    @abc.abstractmethod
    def list(self) -> list[ExternalComputer]: ...
