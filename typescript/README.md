# TypeScript — MIOSA × Orgo

Same adapter as the Python package, in TypeScript. Uses global `fetch` (Node 18+).

```bash
cd typescript
npm install
ORGO_API_KEY=sk_live_... npm run demo      # provision → drive → destroy
npm run typecheck
```

- `src/provider.ts` — the `ExternalComputer` / `ComputeProvider` contract
- `src/orgo.ts` — Orgo implementation (`OrgoProvider`, `OrgoComputer`, `.prompt()`)
- `src/tools.ts` — control primitives as tool schemas + `dispatch()` for your own agent
- `demo.ts` — end-to-end example

Keep `ORGO_API_KEY` server-side. Never ship it to a browser.
