# MIOSA × Orgo — bring Orgo computers into your app

Plug an [Orgo](https://orgo.ai) computer into a MIOSA application and drive it
with **MIOSA's own agent (Optimal), a hosted model, or your own harness** — over
the same `Computer` surface as a native MIOSA box.

Orgo competes with MIOSA on raw computer-use VMs. This turns Orgo into a *supply
source*: Orgo gives you the machine, **you keep the orchestration layer, the
agent, and the user relationship**.

📖 Docs: **https://miosa.ai/docs/integrations/external-computers** ·
💰 Comparison: **https://miosa.ai/docs/integrations/comparison**

---

## If you're a MIOSA white-label customer

You run your product on MIOSA — your own brand, your own domain, your users
never see "MIOSA". This repo is how you let **your end-users** get an Orgo
computer and run agents on it, from inside **your** app, in **your** workspace:

1. **Your app is a MIOSA deployment.** Ship it with `miosa deploy` (see
   [Deploy docs](https://miosa.ai/docs/deploy/overview)). It runs on the same
   substrate as the computers it orchestrates.
2. **Each of your users gets an isolated Orgo computer** — through the same
   interface as a native MIOSA computer.
3. **Your users issue agents.** Optimal, a hosted model, or a harness you write —
   the agent drives the box; your user sees the result. Keys never leave your
   server.
4. **Usage rolls up per user** to your MIOSA workspace for billing and quotas
   ([attribution](https://miosa.ai/docs/platform/attribution)).

`platform_server.py` is a complete reference for steps 2–3. `openapi.yaml`
documents the API your app exposes.

```bash
ORGO_API_KEY=sk_live_... python platform_server.py
# POST /users/alice/computer      → provision an isolated Orgo box for "alice"
# POST /users/alice/agent         → {"goal":"...", "harness":"model"}  run an agent on it
# DELETE /users/alice/computer    → tear it down
```

---

## Bring your own harness

Building your own agent on your own platform? You don't need our loop — you need
the controls. `tools.py` exposes the Orgo computer as standard tool/function
schemas + a dispatcher, so you can drop it straight into your agent:

```python
from external_compute import OrgoProvider
from tools import TOOL_SCHEMAS, dispatch

computer = OrgoProvider().create(name="agent-box")

# advertise the tools to your model (OpenAI-style; tools.anthropic_tools() for Anthropic)
resp = your_llm.create(model=..., tools=TOOL_SCHEMAS, messages=[...])

# run whatever the model calls, on the Orgo box, and feed results back
for call in resp.tool_calls:
    result = dispatch(computer, call.name, call.arguments)
```

Tools provided: `exec`, `screenshot`, `left_click`, `type`, `key`,
`write_file`, `read_file`. The same primitives the built-in harnesses use.

---

## How it works

A harness depends only on `ExternalComputer` — it never knows it's talking to
Orgo. Surface mapping, **verified live against the Orgo API (2026-06-09):**

| `ExternalComputer` | Orgo |
|---|---|
| `exec()` / `python()` | `POST /computers/{id}/bash` · `/exec` |
| `shell_endpoint()` | WS terminal `wss://…/ws/terminal` (**no port 22**) |
| `screenshot()` | `GET /computers/{id}/screenshot` |
| `left_click/type/key` | `POST /computers/{id}/{action}` |
| `read_file/write_file` | via `bash` |
| `preview_url(port)` | ❌ Orgo has no general ingress → use a [MIOSA tunnel](https://miosa.ai/docs/computers/byoc#tunnels) |
| `stop/destroy` | `POST /stop` · `DELETE /computers/{id}` |

## Quick start

```bash
pip install -r requirements.txt
export ORGO_API_KEY=sk_live_...

python demo.py                    # ProbeHarness — no LLM, proves the wiring
python demo.py --harness model    # drive with MIOSA's hosted model (needs MIOSA_API_KEY)
python demo.py --harness optimal  # bind MIOSA's Optimal agent (sketch)
```

### Built-in harnesses

- `ProbeHarness` — deterministic, no model. End-to-end wiring check.
- `MiosaModelHarness` — drives the box with MIOSA's hosted model.
- `OptimalHarness` — hands the box to MIOSA's Optimal agent.
- **Custom** — see "Bring your own harness" above, or subclass `Harness`.

## Benchmark

```bash
python benchmark.py --only orgo --runs 12 --json            # Orgo only
MIOSA_API_KEY=msk_... python benchmark.py --runs 12         # Orgo vs MIOSA, like-for-like
```

Latest measured results: [`results/orgo-benchmark.json`](results/orgo-benchmark.json).

| metric | orgo (measured 2026-06-09) |
|---|---|
| boot — warm pool / cold | 272 ms / 3.13 s |
| desktop-ready | 2.09 s |
| exec p50 / p95 | 100 ms / 116 ms |
| python / file-write / click p50 | 206 ms / 100 ms / 200 ms |
| screenshot p50 | 290 ms – 1.19 s |

## Layout

```
external_compute/
  provider.py        # the contract: ComputeProvider + ExternalComputer
  orgo_provider.py   # Orgo implementation (verified against the live API)
  miosa_provider.py  # MIOSA implementation (wraps the miosa SDK) for comparison
harness.py           # Probe / MiosaModel / Optimal / your-own orchestrators
tools.py             # control primitives as agent tool schemas + dispatcher
platform_server.py   # embed in YOUR app: provision per-user + issue agents
demo.py              # connect → drive → teardown
benchmark.py         # Orgo vs MIOSA on boot/exec/screenshot
openapi.yaml         # API spec for platform_server
results/             # measured benchmark output (JSON)
```

## Security

- Keep `ORGO_API_KEY` (`sk_live_...`) and `MIOSA_API_KEY` (`msk_...`) server-side. Never ship them to a browser.
- Store each end-user's Orgo key encrypted and scope a MIOSA workspace per user so boxes roll up to the right tenant.

## License

Apache-2.0.

---

*This repo is Orgo-specific. Other external providers (E2B, Daytona, …) get their
own repos under [Miosa-osa](https://github.com/Miosa-osa) — all implement the same
`ExternalComputer` contract, so harnesses port across them unchanged.*
