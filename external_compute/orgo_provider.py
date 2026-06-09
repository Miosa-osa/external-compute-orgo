"""Orgo implementation of the normalized external-compute interface.

Every endpoint and field below was verified live against the real Orgo API
(base ``https://www.orgo.ai/api``, Bearer auth) on 2026-06-09:

    POST /computers                      {workspace_id(uuid), name} -> {id, instance_id, url, ...}
    POST /computers/{id}/bash            {command}                  -> {output, exit_code, error}
    POST /computers/{id}/exec            {code}            (python)
    GET  /computers/{id}/screenshot                                 -> {image: <storage path>}
    POST /computers/{id}/click|type|key|scroll|drag
    POST /computers/{id}/start|stop|restart|clone
    GET  /workspaces                                                -> {projects: [{id, ...}]}

Orgo exposes shell access as a WebSocket terminal, NOT port-22 SSH, and has no
general port ingress (only RTMP streaming) — both reflected here.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from .provider import (
    ComputeProvider,
    ComputerInfo,
    ExecResult,
    ExternalComputer,
    ShellEndpoint,
)

ORGO_API_BASE = os.environ.get("ORGO_API_BASE", "https://www.orgo.ai/api")
DEFAULT_TIMEOUT = 180


class OrgoComputer(ExternalComputer):
    def __init__(self, session: requests.Session, base: str, data: dict) -> None:
        self._s = session
        self._base = base
        self._data = data

    # ── identity ──────────────────────────────────────────────────────────
    @property
    def info(self) -> ComputerInfo:
        return ComputerInfo(
            id=self._data["id"],
            name=self._data.get("name", ""),
            provider="orgo",
            status=self._data.get("status", "unknown"),
            public_url=self._data.get("url") or self._data.get("connection_url"),
            raw=self._data,
        )

    def _post(self, path: str, json: dict, *, timeout: int = DEFAULT_TIMEOUT) -> dict:
        r = self._s.post(f"{self._base}/computers/{self._data['id']}{path}", json=json, timeout=timeout)
        r.raise_for_status()
        return r.json()

    # ── orchestration core (the "SSH path") ───────────────────────────────
    def exec(self, command: str, *, timeout: Optional[int] = None) -> ExecResult:
        body = self._post("/bash", {"command": command}, timeout=timeout or DEFAULT_TIMEOUT)
        return ExecResult(
            output=body.get("output", ""),
            exit_code=int(body.get("exit_code", 0) if body.get("success") else (body.get("exit_code") or 1)),
            error=body.get("error"),
        )

    def python(self, code: str, *, timeout: Optional[int] = None) -> ExecResult:
        body = self._post("/exec", {"code": code}, timeout=timeout or DEFAULT_TIMEOUT)
        return ExecResult(output=body.get("output", ""), exit_code=0 if body.get("success") else 1, error=body.get("error"))

    def shell_endpoint(self) -> ShellEndpoint:
        # Orgo: WebSocket terminal, password = vnc_password. No port-22 SSH.
        instance = self._data.get("instance_id") or self._data.get("fly_instance_id", "")
        token = self._data.get("vnc_password", "")
        return ShellEndpoint(
            kind="websocket",
            uri=f"wss://www.orgo.ai/desktops/{instance}/ws/terminal?token={token}&cols=120&rows=32",
            token=token,
            meta={"instance_id": instance},
        )

    # ── computer-use ──────────────────────────────────────────────────────
    def screenshot(self) -> bytes:
        r = self._s.get(f"{self._base}/computers/{self._data['id']}/screenshot", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        body = r.json()
        # Orgo returns a storage path; fetch the actual bytes.
        img_path = body.get("image", "")
        if img_path.startswith("/"):
            img = self._s.get(f"https://www.orgo.ai{img_path}", timeout=DEFAULT_TIMEOUT)
            img.raise_for_status()
            return img.content
        return img_path.encode()

    def left_click(self, x: int, y: int) -> None:
        self._post("/click", {"x": x, "y": y})

    def type(self, text: str) -> None:
        self._post("/type", {"text": text})

    def key(self, key: str) -> None:
        self._post("/key", {"key": key})

    # ── files (via bash; Orgo's /files API is workspace-scoped multipart) ──
    def write_file(self, path: str, content: str) -> None:
        # Heredoc keeps it provider-agnostic and avoids the multipart upload flow.
        import shlex

        self.exec(f"cat > {shlex.quote(path)} <<'__MIOSA_EOF__'\n{content}\n__MIOSA_EOF__")

    def read_file(self, path: str) -> str:
        import shlex

        return self.exec(f"cat {shlex.quote(path)}").output

    # ── port ingress: NOT supported by Orgo → caller falls back to MIOSA tunnel
    # (inherits NotImplementedError from base; that's the signal, not a bug)

    # ── lifecycle ─────────────────────────────────────────────────────────
    def stop(self) -> None:
        self._post("/stop", {})

    def destroy(self) -> None:
        r = self._s.delete(f"{self._base}/computers/{self._data['id']}", timeout=DEFAULT_TIMEOUT)
        if r.status_code not in (200, 204, 404):
            r.raise_for_status()


class OrgoProvider(ComputeProvider):
    name = "orgo"

    def __init__(self, api_key: Optional[str] = None, *, workspace_id: Optional[str] = None, base: str = ORGO_API_BASE) -> None:
        key = api_key or os.environ.get("ORGO_API_KEY")
        if not key:
            raise RuntimeError("Set ORGO_API_KEY or pass api_key=")
        self._base = base
        self._s = requests.Session()
        self._s.headers.update({"Authorization": f"Bearer {key}", "content-type": "application/json"})
        self._workspace_id = workspace_id or os.environ.get("ORGO_WORKSPACE_ID") or self._default_workspace()

    def _default_workspace(self) -> str:
        r = self._s.get(f"{self._base}/workspaces", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        projects = r.json().get("projects", [])
        if not projects:
            raise RuntimeError("No Orgo workspace found for this API key")
        return projects[0]["id"]

    def create(self, *, name: str, **opts) -> OrgoComputer:
        body = {"workspace_id": self._workspace_id, "name": name, **opts}
        r = self._s.post(f"{self._base}/computers", json=body, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return OrgoComputer(self._s, self._base, r.json())

    def get(self, computer_id: str) -> OrgoComputer:
        r = self._s.get(f"{self._base}/computers/{computer_id}", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return OrgoComputer(self._s, self._base, r.json())

    def list(self) -> list[OrgoComputer]:
        r = self._s.get(f"{self._base}/workspaces", timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        out: list[OrgoComputer] = []
        for ws in r.json().get("projects", []):
            for d in ws.get("desktops", []):
                out.append(OrgoComputer(self._s, self._base, d))
        return out
