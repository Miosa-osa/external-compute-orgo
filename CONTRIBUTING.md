# Contributing

This repo implements the MIOSA **external computer** contract for Orgo. The same
contract powers other providers in their own repos — keep changes provider-neutral
where they touch `external_compute/provider.py`.

## Dev setup

```bash
pip install -r requirements.txt pytest
make test          # unit tests (no network — fake transport)
make lint          # compile-check every module
```

TypeScript:

```bash
cd typescript && npm install
npm run typecheck
```

## Adding a new provider

1. Implement `ComputeProvider` + `ExternalComputer` in a new module.
2. Map your provider's API to the normalized surface (see `orgo_provider.py`).
3. Where the provider can't back a capability (e.g. port ingress), let the base
   method raise `NotImplementedError` — harnesses feature-detect on that.
4. Add tests against a fake transport (see `tests/conftest.py`).

## Tests

Unit tests never hit the network — `OrgoProvider(session=FakeSession())` injects a
canned transport. Live checks (`demo.py`, `benchmark.py`) require a real
`ORGO_API_KEY` and are not run in CI.

## Style

- Keep the public surface identical across Python and TypeScript.
- Keys (`ORGO_API_KEY`, `MIOSA_API_KEY`) stay server-side. Never log them.
