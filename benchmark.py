"""Benchmark external providers against MIOSA on the metrics that matter for
agent orchestration: provision/boot, desktop-ready, exec round-trip, screenshot.

    export ORGO_API_KEY=sk_live_...
    export MIOSA_API_KEY=msk_...        # optional; omit to bench Orgo only
    python benchmark.py --runs 20
    python benchmark.py --only orgo

All numbers come from real API calls — no estimates. Results print as a table
and as JSON (for the /docs/benchmarks page).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from external_compute import ComputeProvider, ExternalComputer, OrgoProvider


@dataclass
class Metric:
    samples: list[float] = field(default_factory=list)

    def add(self, ms: float) -> None:
        self.samples.append(ms)

    def summary(self) -> dict:
        if not self.samples:
            return {"n": 0}
        s = sorted(self.samples)
        return {
            "n": len(s),
            "p50_ms": round(statistics.median(s), 1),
            "p95_ms": round(s[min(len(s) - 1, int(len(s) * 0.95))], 1),
            "mean_ms": round(statistics.fmean(s), 1),
            "min_ms": round(s[0], 1),
            "max_ms": round(s[-1], 1),
        }


@dataclass
class ProviderResult:
    provider: str
    boot_ms: Optional[float] = None
    desktop_ready_ms: Optional[float] = None
    exec: Metric = field(default_factory=Metric)
    file_write: Metric = field(default_factory=Metric)
    click: Metric = field(default_factory=Metric)
    screenshot: Metric = field(default_factory=Metric)
    error: Optional[str] = None


def _ms(fn: Callable) -> float:
    t = time.time()
    fn()
    return (time.time() - t) * 1000.0


def bench_provider(provider: ComputeProvider, *, runs: int, name: str) -> ProviderResult:
    res = ProviderResult(provider=provider.name)
    computer: Optional[ExternalComputer] = None
    try:
        # 1) provision / boot
        t0 = time.time()
        computer = provider.create(name=name)
        res.boot_ms = round((time.time() - t0) * 1000.0, 1)

        # 2) desktop-ready = first successful exec (the box can take commands)
        t = time.time()
        for _ in range(60):
            try:
                if computer.exec("true").exit_code == 0:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        res.desktop_ready_ms = round((time.time() - t) * 1000.0, 1)

        # 3) exec round-trip
        for i in range(runs):
            res.exec.add(_ms(lambda: computer.exec(f"echo {i}")))

        # 3b) file write
        for i in range(max(3, runs // 3)):
            try:
                res.file_write.add(_ms(lambda: computer.write_file(f"/tmp/bench-{i}", "x")))
            except NotImplementedError:
                break

        # 3c) computer-use click
        for _ in range(max(3, runs // 3)):
            try:
                res.click.add(_ms(lambda: computer.left_click(100, 100)))
            except NotImplementedError:
                break

        # 4) screenshot latency
        for _ in range(max(3, runs // 4)):
            try:
                res.screenshot.add(_ms(lambda: computer.screenshot()))
            except NotImplementedError:
                break
    except Exception as e:  # noqa: BLE001
        res.error = f"{type(e).__name__}: {e}"
    finally:
        if computer is not None:
            try:
                computer.destroy()
            except Exception:
                pass
    return res


def print_table(results: list[ProviderResult]) -> None:
    cols = ["metric"] + [r.provider for r in results]
    rows = [
        ["boot (provision)", *[_fmt(r.boot_ms) for r in results]],
        ["desktop-ready", *[_fmt(r.desktop_ready_ms) for r in results]],
        ["exec p50", *[_fmt(r.exec.summary().get("p50_ms")) for r in results]],
        ["exec p95", *[_fmt(r.exec.summary().get("p95_ms")) for r in results]],
        ["file write p50", *[_fmt(r.file_write.summary().get("p50_ms")) for r in results]],
        ["click p50", *[_fmt(r.click.summary().get("p50_ms")) for r in results]],
        ["screenshot p50", *[_fmt(r.screenshot.summary().get("p50_ms")) for r in results]],
    ]
    w = [max(len(str(x)) for x in [cols[i]] + [row[i] for row in rows]) for i in range(len(cols))]
    line = lambda cells: " | ".join(str(c).ljust(w[i]) for i, c in enumerate(cells))
    print("\n" + line(cols))
    print("-+-".join("-" * x for x in w))
    for row in rows:
        print(line(row))
    for r in results:
        if r.error:
            print(f"\n! {r.provider} error: {r.error}")


def _fmt(v) -> str:
    return "—" if v is None else f"{v:.0f}ms" if v < 10000 else f"{v/1000:.1f}s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--only", choices=["orgo", "miosa"], default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    providers: list[ComputeProvider] = []
    if args.only in (None, "orgo"):
        providers.append(OrgoProvider())
    if args.only in (None, "miosa"):
        try:
            from external_compute import MiosaProvider

            providers.append(MiosaProvider())
        except Exception as e:  # noqa: BLE001
            print(f"(skipping MIOSA: {e})")

    results = [bench_provider(p, runs=args.runs, name=f"bench-{p.name}") for p in providers]
    print_table(results)
    if args.json:
        print(
            "\n"
            + json.dumps(
                [
                    asdict(r)
                    | {
                        "exec": r.exec.summary(),
                        "file_write": r.file_write.summary(),
                        "click": r.click.summary(),
                        "screenshot": r.screenshot.summary(),
                    }
                    for r in results
                ],
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
