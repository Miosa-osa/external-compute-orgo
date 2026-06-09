"""End-to-end demo: plug an Orgo computer into MIOSA orchestration.

    export ORGO_API_KEY=sk_live_...
    python demo.py                 # uses ProbeHarness (no LLM, no extra keys)
    python demo.py --keep          # don't destroy the box afterwards
    python demo.py --harness model # drive with MIOSA's hosted model (needs MIOSA_API_KEY)

This is the literal answer to "let people bring their Orgo computers into our
app and orchestrate them with our agent": connect provider -> get a normalized
computer -> hand it to any harness.
"""

from __future__ import annotations

import argparse
import sys
import time

from external_compute import OrgoProvider
from harness import MiosaModelHarness, OptimalHarness, ProbeHarness

HARNESSES = {
    "probe": ProbeHarness,
    "model": MiosaModelHarness,
    "optimal": OptimalHarness,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness", choices=HARNESSES, default="probe")
    ap.add_argument("--goal", default="report the OS and CPU count")
    ap.add_argument("--keep", action="store_true", help="don't destroy the box")
    ap.add_argument("--name", default="miosa-orgo-demo")
    args = ap.parse_args()

    provider = OrgoProvider()
    print(f"→ provider: {provider.name}")

    t0 = time.time()
    computer = provider.create(name=args.name)
    boot = time.time() - t0
    print(f"→ created {computer.info.id} in {boot:.2f}s (status={computer.info.status})")

    try:
        harness = HARNESSES[args.harness]()
        print(f"→ harness: {args.harness}\n")
        print(harness.run(computer, args.goal))
    finally:
        if args.keep:
            print(f"\n(kept {computer.info.id} — destroy with the Orgo dashboard or get()+destroy())")
        else:
            computer.destroy()
            print(f"\n→ destroyed {computer.info.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
