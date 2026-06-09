"""Tests for the agent-tool layer (schemas + dispatch)."""

from __future__ import annotations

from external_compute.provider import ExecResult, ExternalComputer
from tools import TOOL_SCHEMAS, anthropic_tools, dispatch


class StubComputer(ExternalComputer):
    """Minimal ExternalComputer that records what was called."""

    def __init__(self):
        self.events = []

    @property
    def info(self):  # not used here
        raise NotImplementedError

    def exec(self, command, *, timeout=None):
        self.events.append(("exec", command))
        return ExecResult(output=f"ran:{command}", exit_code=0)

    def shell_endpoint(self):
        raise NotImplementedError

    def screenshot(self):
        self.events.append(("screenshot", None))
        return b"\x89PNG"

    def left_click(self, x, y):
        self.events.append(("left_click", (x, y)))

    def type(self, text):
        self.events.append(("type", text))

    def key(self, key):
        self.events.append(("key", key))

    def write_file(self, path, content):
        self.events.append(("write_file", (path, content)))

    def read_file(self, path):
        self.events.append(("read_file", path))
        return "file-contents"

    def stop(self):
        ...

    def destroy(self):
        ...


def test_tool_schema_names_cover_dispatch():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {"exec", "screenshot", "left_click", "type", "key", "write_file", "read_file"}


def test_dispatch_exec():
    c = StubComputer()
    out = dispatch(c, "exec", {"command": "ls"})
    assert out == {"output": "ran:ls", "exit_code": 0, "error": None}
    assert ("exec", "ls") in c.events


def test_dispatch_screenshot_is_base64():
    c = StubComputer()
    out = dispatch(c, "screenshot", {})
    assert "image_base64" in out
    import base64

    assert base64.b64decode(out["image_base64"]) == b"\x89PNG"


def test_dispatch_click_and_read_file():
    c = StubComputer()
    assert dispatch(c, "left_click", {"x": 10, "y": 20}) == {"ok": True}
    assert ("left_click", (10, 20)) in c.events
    assert dispatch(c, "read_file", {"path": "/x"})["content"] == "file-contents"


def test_dispatch_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        dispatch(StubComputer(), "nope", {})


def test_anthropic_tools_shape():
    a = anthropic_tools()
    assert all("input_schema" in t and "name" in t for t in a)
    assert len(a) == len(TOOL_SCHEMAS)
