"""MIOSA implementation of the same normalized interface.

This wraps the official ``miosa`` Python SDK so a MIOSA cloud computer satisfies
exactly the same ``ExternalComputer`` contract as an Orgo box. That lets the
benchmark and any harness compare the two — or move work between them — without
branching on the vendor.
"""

from __future__ import annotations

import os
from typing import Optional

from .provider import (
    ComputeProvider,
    ComputerInfo,
    ExecResult,
    ExternalComputer,
    ShellEndpoint,
)


class MiosaComputer(ExternalComputer):
    def __init__(self, computer) -> None:  # miosa.resources.computer.Computer
        self._c = computer

    @property
    def info(self) -> ComputerInfo:
        return ComputerInfo(
            id=self._c.id,
            name=self._c.name,
            provider="miosa-cloud",
            status=self._c.status,
            public_url=self._safe(lambda: self._c.public_url()),
        )

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return None

    def exec(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        res = self._c.bash(command, timeout=timeout)
        return ExecResult(output=getattr(res, "output", str(res)), exit_code=getattr(res, "exit_code", 0))

    def shell_endpoint(self) -> ShellEndpoint:
        # MIOSA: real SSH / envd exec channel.
        return ShellEndpoint(kind="exec-only", uri=f"miosa://{self._c.id}", meta={"computer_id": self._c.id})

    def screenshot(self) -> bytes:
        return self._c.screenshot()

    def left_click(self, x: int, y: int) -> None:
        self._c.left_click(x, y)

    def type(self, text: str) -> None:
        self._c.type(text)

    def key(self, key: str) -> None:
        self._c.key(key)

    def write_file(self, path: str, content: str) -> None:
        self._c.write_file(path, content)

    def read_file(self, path: str) -> str:
        return self._c.read_file(path)

    def preview_url(self, port: int, path: str = "/") -> str:
        return self._c.preview_url(port, path)

    def stop(self) -> None:
        self._c.stop()

    def destroy(self) -> None:
        self._c.destroy()


class MiosaProvider(ComputeProvider):
    name = "miosa-cloud"

    def __init__(self, api_key: Optional[str] = None, *, template: str = "miosa-desktop") -> None:
        from miosa import Miosa

        self._client = Miosa(api_key=api_key or os.environ["MIOSA_API_KEY"])
        self._template = template

    def create(self, *, name: str, **opts) -> MiosaComputer:
        c = self._client.computers.create(name=name, template_type=opts.pop("template", self._template), **opts)
        return MiosaComputer(c)

    def get(self, computer_id: str) -> MiosaComputer:
        return MiosaComputer(self._client.computers.get(computer_id))

    def list(self) -> list[MiosaComputer]:
        return [MiosaComputer(c) for c in self._client.computers.list()]
