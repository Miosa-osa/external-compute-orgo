# External Compute Providers — plug Orgo into MIOSA

Let your users bring a **third-party computer** (here: [Orgo](https://orgo.ai))
into a MIOSA application, then orchestrate it with **MIOSA's own agent, hosted
model, or the user's custom harness** — over the same `Computer` surface as a
native MIOSA box.

Orgo competes with MIOSA on raw computer-use VMs. This integration absorbs them
as a *compute source*: they supply the machine, MIOSA owns the orchestration
layer and the user relationship.

> The same pattern works for E2B, Daytona, or any provider that gives you
> `create` + `exec` + (optionally) computer-use actions. Implement the
> `ComputeProvider` / `ExternalComputer` contract in `external_compute/provider.py`
> and everything else — harnesses, benchmark, demo — works unchanged.

## The model

MIOSA already has three compute substrates behind one API:

| Source | Where it runs |
|---|---|
| `miosa-cloud` | Firecracker microVMs on MIOSA's fleet |
| `opencomputers` | the user's own hardware (BYOC) over outbound WS |
| **`external`** | **a third-party provider (this example)** |

A harness depends only on `ExternalComputer`. It never branches on the vendor.

## Surface mapping (verified live, 2026-06-09)

| `ExternalComputer` | Orgo reality |
|---|---|
| `exec()` | `POST /computers/{id}/bash` → `{output, exit_code}` |
| `python()` | `POST /computers/{id}/exec` |
| `shell_endpoint()` | WS terminal `wss://…/desktops/{instance}/ws/terminal` (**no port 22**) |
| `screenshot()` | `GET /computers/{id}/screenshot` |
| `left_click/type/key` | `POST /computers/{id}/{action}` |
| `read_file/write_file` | via `bash` heredoc/cat (Orgo `/files` is workspace-scoped) |
| `preview_url(port)` | ❌ **not supported** — Orgo has no general ingress; use a MIOSA edge tunnel |
| `stop/destroy` | `POST /stop`, `DELETE /computers/{id}` |

The one real gap is **port ingress**: Orgo only exposes RTMP streaming, not
arbitrary ports. When `preview_url()` raises `NotImplementedError`, route the
port through MIOSA's edge tunnel (same mechanism as the BYOC tunnel) so the
external box still serves previews under your domain.

## Run it

```bash
pip install -r requirements.txt
export ORGO_API_KEY=sk_live_...        # your Orgo key

python demo.py                          # ProbeHarness — no LLM, proves the wiring
python demo.py --harness model --goal "list installed python packages"   # needs MIOSA_API_KEY
python demo.py --harness optimal        # sketch of binding Optimal to the box
python demo.py --keep                   # leave the box running
```

### Harnesses (`harness.py`) — "all of the above + your own"

- `ProbeHarness` — deterministic, no model. End-to-end wiring check.
- `MiosaModelHarness` — drives the box with MIOSA's hosted model (completions API).
- `OptimalHarness` — hands the box to MIOSA's Optimal agent (wiring sketch).
- **Custom** — subclass `Harness` and implement `run(computer, goal)`. The
  computer handle is provider-neutral; bring any loop (Claude Computer Use,
  your own ReAct, etc.).

## Benchmark

```bash
python benchmark.py --only orgo --runs 12 --json   # Orgo only
MIOSA_API_KEY=msk_... python benchmark.py --runs 12  # Orgo vs MIOSA, like-for-like
```

Measures provision/boot, **desktop-ready** (first command accepted),
exec round-trip, and screenshot latency — both providers through the *same*
interface, so the comparison is apples-to-apples.

### Live result — Orgo (12 runs, 2026-06-09, from a US laptop)

| metric | orgo |
|---|---|
| boot (provision API) | 272 ms |
| desktop-ready | 2.09 s |
| exec p50 / p95 | 100 ms / 116 ms |
| screenshot p50 | 1185 ms |

Run with `MIOSA_API_KEY` set to drop the MIOSA column in next to it. (MIOSA
sandbox snapshot-restore boots ~166 ms p50; see `/docs/benchmarks`.)

## Files

```
external_compute/
  provider.py        # the contract: ComputeProvider + ExternalComputer
  orgo_provider.py   # Orgo implementation (verified against the live API)
  miosa_provider.py  # MIOSA implementation (wraps the miosa SDK) for comparison
harness.py           # Probe / MiosaModel / Optimal / your-own orchestrators
demo.py              # connect → drive → teardown
benchmark.py         # Orgo vs MIOSA on the metrics that matter
```

## Security

- Keep `ORGO_API_KEY` (`sk_live_...`) server-side. Never ship it to a browser.
- In a real product, store each user's provider key encrypted and scope a MIOSA
  workspace per user so external boxes roll up to the right tenant for billing.
