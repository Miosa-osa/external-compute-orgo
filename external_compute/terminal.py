"""WebSocket terminal helper — the interactive "SSH-like" channel to an Orgo box.

Orgo exposes a shell as a WebSocket terminal (there is no port 22). This wraps
``computer.shell_endpoint()`` so a harness can stream an interactive PTY instead
of one-shot ``exec`` calls.

    pip install websocket-client
    from external_compute import OrgoProvider
    from external_compute.terminal import open_terminal

    c = OrgoProvider().create(name="box")
    term = open_terminal(c)
    term.send("ls -la\n")
    print(term.read(timeout=2))
    term.close()
"""

from __future__ import annotations

from typing import Optional

from .provider import ExternalComputer


class Terminal:
    def __init__(self, ws) -> None:
        self._ws = ws

    def send(self, data: str) -> None:
        self._ws.send(data)

    def read(self, timeout: float = 1.0) -> str:
        self._ws.settimeout(timeout)
        chunks = []
        try:
            while True:
                chunks.append(self._ws.recv())
        except Exception:
            pass
        return "".join(c if isinstance(c, str) else c.decode("utf-8", "replace") for c in chunks)

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


def open_terminal(computer: ExternalComputer) -> Terminal:
    """Open an interactive terminal to the computer's shell endpoint."""
    try:
        from websocket import create_connection
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pip install websocket-client to use open_terminal()") from e

    ep = computer.shell_endpoint()
    if ep.kind != "websocket":
        raise RuntimeError(f"shell endpoint kind {ep.kind!r} is not a websocket terminal")
    return Terminal(create_connection(ep.uri))
