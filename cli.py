"""Tiny CLI for driving an Orgo computer from your terminal.

    ORGO_API_KEY=sk_live_... python cli.py create --name box
    ORGO_API_KEY=sk_live_... python cli.py exec <id> "uname -a"
    ORGO_API_KEY=sk_live_... python cli.py shot <id> out.png
    ORGO_API_KEY=sk_live_... python cli.py prompt <id> "open chrome"
    ORGO_API_KEY=sk_live_... python cli.py ls
    ORGO_API_KEY=sk_live_... python cli.py rm <id>
"""

from __future__ import annotations

import argparse
import sys

from external_compute import OrgoProvider


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="orgo-cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create"); c.add_argument("--name", default="cli-box")
    e = sub.add_parser("exec"); e.add_argument("id"); e.add_argument("command")
    s = sub.add_parser("shot"); s.add_argument("id"); s.add_argument("out", nargs="?", default="screenshot.png")
    p = sub.add_parser("prompt"); p.add_argument("id"); p.add_argument("instruction")
    sub.add_parser("ls")
    r = sub.add_parser("rm"); r.add_argument("id")

    args = ap.parse_args(argv)
    provider = OrgoProvider()

    if args.cmd == "create":
        c = provider.create(name=args.name)
        print(c.info.id, c.info.status)
    elif args.cmd == "exec":
        res = provider.get(args.id).exec(args.command)
        sys.stdout.write(res.output)
        return res.exit_code
    elif args.cmd == "shot":
        data = provider.get(args.id).screenshot()
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"wrote {len(data)} bytes -> {args.out}")
    elif args.cmd == "prompt":
        print(provider.get(args.id).prompt(args.instruction))
    elif args.cmd == "ls":
        for c in provider.list():
            print(c.info.id, c.info.status, c.info.name)
    elif args.cmd == "rm":
        provider.get(args.id).destroy()
        print("destroyed", args.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
