from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_agent_registry
from .models import AgentConfig
from .runner import run_suite
from .suites import load_suite


PROJECT_ROOT = Path.cwd()
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "agents.yaml"
DEFAULT_EVAL_DIR = PROJECT_ROOT / "evals"
DEFAULT_RUNS_DIR = PROJECT_ROOT / "runs"


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentops-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create runtime directories.")

    list_parser = subparsers.add_parser("list-agents", help="List configured agents.")
    list_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    run_parser = subparsers.add_parser("run", help="Run an eval suite.")
    run_parser.add_argument("--suite", default="sample", help="Suite name from evals/<name>.jsonl.")
    run_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument(
        "--agent",
        action="append",
        default=None,
        help="Run only the named agent. Repeat to select multiple agents.",
    )

    report_parser = subparsers.add_parser("report", help="Print run summary.")
    report_parser.add_argument("--run", default="latest")
    report_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)

    args = parser.parse_args()

    if args.command == "init":
        DEFAULT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Initialized {DEFAULT_RUNS_DIR}")
        return 0

    if args.command == "list-agents":
        agents = load_agent_registry(args.config)
        for agent in agents:
            print(f"{agent.name}\t{agent.timeout_seconds}s\t{agent.command}")
        return 0

    if args.command == "run":
        agents = load_agent_registry(args.config)
        agents = _select_agents(agents, args.agent)
        cases = load_suite(DEFAULT_EVAL_DIR / f"{args.suite}.jsonl")
        run_dir = run_suite(agents, cases, args.runs_dir, args.run_id)
        print(f"Run complete: {run_dir} ({len(agents)} agent(s), {len(cases)} case(s))")
        return 0

    if args.command == "report":
        run_id = _resolve_run_id(args.runs_dir, args.run)
        summary_path = args.runs_dir / run_id / "summary.json"
        debug_path = args.runs_dir / run_id / "debug.md"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(json.dumps(summary, indent=2))
        print(f"Debug report: {debug_path}")
        return 0

    return 1


def _resolve_run_id(runs_dir: Path, run: str) -> str:
    if run != "latest":
        return run
    latest_path = runs_dir / "latest.txt"
    if not latest_path.exists():
        raise SystemExit("No latest run found. Run an eval first.")
    return latest_path.read_text(encoding="utf-8").strip()


def _select_agents(agents: list[AgentConfig], selected_names: list[str] | None) -> list[AgentConfig]:
    if not selected_names:
        return agents

    by_name = {agent.name: agent for agent in agents}
    missing = [name for name in selected_names if name not in by_name]
    if missing:
        available = ", ".join(sorted(by_name))
        requested = ", ".join(missing)
        raise SystemExit(f"Unknown agent(s): {requested}. Available: {available}")

    return [by_name[name] for name in selected_names]


if __name__ == "__main__":
    raise SystemExit(main())
