from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    prompt = sys.stdin.read()
    lower_prompt = prompt.lower()

    if "json" in lower_prompt:
        print(json.dumps({"status": "ok", "component": "eval", "agent": args.name}))
        return 0

    if "secrets" in lower_prompt or "secret" in lower_prompt:
        print(f"{args.name}: secrets must stay private and should not be exposed in eval output.")
        return 0

    print(f"hello from {args.name}: AgentOps evaluation response")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
