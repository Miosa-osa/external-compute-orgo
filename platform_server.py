"""Embed external computers in YOUR platform — and let your users issue agents.

This is the shape you ship when your own product (itself deployed on MIOSA
Deploy) gives each of your end-users an external computer (Orgo, E2B, …) and
lets them run agents on it. Your `msk_*` and provider keys stay server-side;
the browser only ever sees scoped results.

    POST /users/<user_id>/computer       -> provision an external computer for a user
    POST /users/<user_id>/agent          -> issue an agent run on that user's computer
    DELETE /users/<user_id>/computer     -> tear it down

Run locally:
    pip install -r requirements.txt flask
    ORGO_API_KEY=sk_live_... python platform_server.py
    # → http://localhost:8000

Deploy on MIOSA (so your platform and the agents live on the same substrate):
    miosa deploy            # see https://miosa.ai/docs/deploy/overview
"""

from __future__ import annotations

import os
import sys

from external_compute import OrgoProvider
from harness import MiosaModelHarness, OptimalHarness, ProbeHarness

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("pip install flask")
    sys.exit(1)

app = Flask(__name__)
provider = OrgoProvider()  # reads ORGO_API_KEY; swap for any ComputeProvider

# In production: persist this mapping (DB), one computer per end-user, and store
# each user's provider key encrypted. In-memory here for the example.
_user_computers: dict[str, str] = {}

HARNESSES = {"probe": ProbeHarness, "model": MiosaModelHarness, "optimal": OptimalHarness}


@app.post("/users/<user_id>/computer")
def provision(user_id: str):
    """Give this end-user an isolated external computer."""
    computer = provider.create(name=f"user-{user_id}")
    _user_computers[user_id] = computer.info.id
    return jsonify({"computer_id": computer.info.id, "provider": computer.info.provider, "status": computer.info.status})


@app.post("/users/<user_id>/agent")
def run_agent(user_id: str):
    """Issue an agent run on the user's computer.

    Body: {"goal": "...", "harness": "probe|model|optimal"}
    The harness is provider-neutral — it drives the external box the same way it
    would a native MIOSA computer.
    """
    cid = _user_computers.get(user_id)
    if not cid:
        return jsonify({"error": "no computer for user; POST /users/<id>/computer first"}), 404

    body = request.get_json(silent=True) or {}
    harness_name = body.get("harness", "probe")
    goal = body.get("goal", "report the OS and CPU count")
    if harness_name not in HARNESSES:
        return jsonify({"error": f"unknown harness; choose {list(HARNESSES)}"}), 400

    computer = provider.get(cid)
    result = HARNESSES[harness_name]().run(computer, goal)
    return jsonify({"computer_id": cid, "harness": harness_name, "goal": goal, "result": result})


@app.delete("/users/<user_id>/computer")
def teardown(user_id: str):
    cid = _user_computers.pop(user_id, None)
    if cid:
        provider.get(cid).destroy()
    return jsonify({"destroyed": bool(cid)})


if __name__ == "__main__":
    if not os.environ.get("ORGO_API_KEY"):
        print("Set ORGO_API_KEY")
        sys.exit(1)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
