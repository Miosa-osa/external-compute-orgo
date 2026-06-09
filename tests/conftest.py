"""Test fixtures — a fake requests.Session so tests never touch the network."""

from __future__ import annotations

import json as _json
from typing import Any, Callable

import pytest


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = content

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Records calls and returns canned responses keyed by (METHOD, path-suffix)."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, str, Any]] = []
        self._routes: dict[str, Callable[[str, Any], FakeResponse]] = {}

    def route(self, method: str, suffix: str, handler: Callable[[str, Any], FakeResponse]) -> None:
        self._routes[f"{method.upper()} {suffix}"] = handler

    def _dispatch(self, method: str, url: str, json: Any = None, **_: Any) -> FakeResponse:
        self.calls.append((method.upper(), url, json))
        for key, handler in self._routes.items():
            m, suffix = key.split(" ", 1)
            if m == method.upper() and url.endswith(suffix):
                return handler(url, json)
        return FakeResponse(404, {"error": "no route", "url": url})

    def get(self, url, **kw):
        return self._dispatch("GET", url, **kw)

    def post(self, url, json=None, **kw):
        return self._dispatch("POST", url, json=json, **kw)

    def delete(self, url, **kw):
        return self._dispatch("DELETE", url, **kw)


@pytest.fixture
def fake_session() -> FakeSession:
    s = FakeSession()
    # default workspace lookup
    s.route("GET", "/workspaces", lambda u, b: FakeResponse(200, {"projects": [{"id": "ws-1", "desktops": []}]}))
    return s
