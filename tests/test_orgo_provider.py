"""Unit tests for the Orgo adapter — no network, fake transport."""

from __future__ import annotations

from conftest import FakeResponse

from external_compute import OrgoProvider


def _provider(fake_session):
    return OrgoProvider(api_key="sk_test", workspace_id="ws-1", session=fake_session)


def test_create_returns_normalized_computer(fake_session):
    fake_session.route(
        "POST",
        "/computers",
        lambda u, b: FakeResponse(200, {"id": "c1", "name": b["name"], "status": "running", "instance_id": "i1", "vnc_password": "pw"}),
    )
    p = _provider(fake_session)
    c = p.create(name="box")
    assert c.info.id == "c1"
    assert c.info.provider == "orgo"
    assert c.info.status == "running"
    # workspace_id from the provider was sent in the body
    _, _, body = [call for call in fake_session.calls if call[0] == "POST"][-1]
    assert body["workspace_id"] == "ws-1"
    assert body["name"] == "box"


def test_exec_maps_bash_response(fake_session):
    fake_session.route("POST", "/computers", lambda u, b: FakeResponse(200, {"id": "c1"}))
    fake_session.route(
        "POST",
        "/c1/bash",
        lambda u, b: FakeResponse(200, {"success": True, "output": "hello\n", "exit_code": 0, "error": None}),
    )
    c = _provider(fake_session).create(name="box")
    r = c.exec("echo hello")
    assert r.output == "hello\n"
    assert r.exit_code == 0
    assert r.ok is True


def test_exec_nonzero_exit(fake_session):
    fake_session.route("POST", "/computers", lambda u, b: FakeResponse(200, {"id": "c1"}))
    fake_session.route("POST", "/c1/bash", lambda u, b: FakeResponse(200, {"success": False, "output": "", "exit_code": 2, "error": "boom"}))
    c = _provider(fake_session).create(name="box")
    r = c.exec("false")
    assert r.exit_code == 2
    assert r.ok is False
    assert r.error == "boom"


def test_shell_endpoint_is_websocket(fake_session):
    fake_session.route("POST", "/computers", lambda u, b: FakeResponse(200, {"id": "c1", "instance_id": "i9", "vnc_password": "tok"}))
    c = _provider(fake_session).create(name="box")
    ep = c.shell_endpoint()
    assert ep.kind == "websocket"
    assert "i9" in ep.uri and "tok" in ep.uri
    assert ep.uri.startswith("wss://")


def test_destroy_tolerates_404(fake_session):
    fake_session.route("POST", "/computers", lambda u, b: FakeResponse(200, {"id": "c1"}))
    fake_session.route("DELETE", "/c1", lambda u, b: FakeResponse(404, {}))
    c = _provider(fake_session).create(name="box")
    c.destroy()  # must not raise


def test_default_workspace_autodiscovered(fake_session):
    # provider built without workspace_id should call /workspaces
    fake_session.route("POST", "/computers", lambda u, b: FakeResponse(200, {"id": "c1"}))
    p = OrgoProvider(api_key="sk_test", session=fake_session)
    assert p._workspace_id == "ws-1"
