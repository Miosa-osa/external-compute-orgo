# MIOSA External Compute — bring any computer into your app

Plug a **third-party computer** ([Orgo](https://orgo.ai), and soon E2B / Daytona)
into a MIOSA application and drive it with **MIOSA's own agent (Optimal), a
hosted model, or your own harness** — over the same `Computer` surface as a
native MIOSA box.

These providers compete with MIOSA on raw computer-use VMs. This turns them into
a *supply source*: they give you the machine, **you keep the orchestration layer,
the agent, and the user relationship**.

📖 Docs: **https://miosa.ai/docs/integrations/external-computers** ·
💰 Comparison: **https://miosa.ai/docs/integrations/comparison**

---

## If you're a MIOSA white-label customer

You run your product on MIOSA — your own brand, your own domain, your users
never see "MIOSA". This repo is how you let **your end-users** get a computer and
run agents on it, from inside **your** app, in **your** workspace:

1. **Your app is a MIOSA deployment.** Ship it with `miosa deploy` (see
   [Deploy docs](https://miosa.ai/docs/deploy/overview)). It runs on the same
   substrate as the computers it orchestrates.
2. **Each of your users gets an isolated computer.** Cloud (MIOSA), their own
   hardware ([BYOC](https://miosa.ai/docs/computers/byoc)), or an **external
   provider** like Orgo — all through one interface.
3. **Your users issue agents.** Optimal, a hosted model, or a harness you write —
   the agent drives the box; your user sees the result. Keys never leave your
   server.
4. **Usage rolls up per user** to your MIOSA workspace for billing and quotas
   ([attribution](https://miosa.ai/docs/platform/attribution)).

`platform_server.py` is a complete reference for steps 2–3. `openapi.yaml`
documents the API your app exposes.

```bash
ORGO_API_KEY=sk_live_... python platform_server.py
# POST /users/alice/computer      → provision an isolated box for "alice"
# POST /users/alice/agent         → {"goal":"...", "harness":"model"}  run an agent on it
# DELETE /users/alice/computer    → tear it down
```

---

## How it works

MIOSA exposes computers on three substrates behind **one** API. A harness
depends only on `ExternalComputer` and never branches on the vendor:

| Source | Where it runs |
|---|---|
| `miosa-cloud` | Firecracker microVMs on MIOSA's fleet |
| `opencomputers` | your own hardware (BYOC) over an outbound WebSocket |
| **`external`** | **a third-party provider — Orgo, E2B, Daytona, …** |

### Surface mapping (verified live against Orgo, 2026-06-09)

| `ExternalComputer` | Orgo |
|---|---|
| `exec()` / `python()` | `POST /computers/{id}/bash` · `/exec` |
| `shell_endpoint()` | WS terminal `wss://…/ws/terminal` (**no port 22**) |
| `screenshot()` | `GET /computers/{id}/screenshot` |
| `left_click/type/key` | `POST /computers/{id}/{action}` |
| `read_file/write_file` | via `bash` |
| `preview_url(port)` | ❌ no general ingress → use a [MIOSA tunnel](https://miosa.ai/docs/computers/byoc#tunnels) |
| `stop/destroy` | `POST /stop` · `DELETE /computers/{id}` |

## Quick start

```bash
pip install -r requirements.txt
export ORGO_API_KEY=sk_live_...

python demo.py                    # ProbeHarness — no LLM, proves the wiring
python demo.py --harness model    # drive with MIOSA's hosted model (needs MIOSA_API_KEY)
python demo.py --harness optimal  # bind MIOSA's Optimal agent (sketch)
```

### Harnesses — "all of the above, plus your own"

- `ProbeHarness` — deterministic, no model. End-to-end wiring check.
- `MiosaModelHarness` — drives the box with MIOSA's hosted model.
- `OptimalHarness` — hands the box to MIOSA's Optimal agent.
- **Custom** — subclass `Harness` and implement `run(computer, goal)`. Bring any
  loop (Claude Computer Use, your own ReAct, etc.).

## Benchmark

```bash
python benchmark.py --only orgo --runs 12 --json            # Orgo only
MIOSA_API_KEY=msk_... python benchmark.py --runs 12         # Orgo vs MIOSA, like-for-like
```

Measures provision/boot, desktop-ready, exec, file-write, click, and screenshot
through the *same* interface. Latest measured results: [`results/orgo-benchmark.json`](results/orgo-benchmark.json).

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
platform_server.py   # embed in YOUR app: provision per-user + issue agents
demo.py              # connect → drive → teardown
benchmark.py         # Orgo vs MIOSA on boot/exec/screenshot
openapi.yaml         # API spec for platform_server
results/             # measured benchmark output (JSON)
```

## Security

- Keep `ORGO_API_KEY` (`sk_live_...`) and `MIOSA_API_KEY` (`msk_...`) server-side. Never ship them to a browser.
- Store each end-user's provider key encrypted and scope a MIOSA workspace per user so external boxes roll up to the right tenant.

## License

Apache-2.0.
