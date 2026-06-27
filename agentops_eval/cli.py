from __future__ import annotations

import argparse
import json
from pathlib import Path

from .baseline import compare_to_baseline, load_summary, promote_baseline
from .calibration import calibrate_judge
from .config import load_agent_registry
from .gate import evaluate_gate
from .models import AgentConfig
from .monitor import run_monitor
from .runner import run_suite
from .suites import load_suite
from .tracing import resolve_trace_path


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
    run_parser.add_argument("--approve-dangerous", action="store_true", help="Allow approved high-risk agent commands.")
    run_parser.add_argument("--judge-command", default="", help="Optional command that scores outputs as JSON {score, reasoning}.")
    run_parser.add_argument(
        "--agent",
        action="append",
        default=None,
        help="Run only the named agent. Repeat to select multiple agents.",
    )

    report_parser = subparsers.add_parser("report", help="Print run summary.")
    report_parser.add_argument("--run", default="latest")
    report_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)

    baseline_parser = subparsers.add_parser("baseline", help="Manage regression baselines.")
    baseline_subparsers = baseline_parser.add_subparsers(dest="baseline_command", required=True)
    promote_parser = baseline_subparsers.add_parser("promote", help="Promote a run summary as a baseline.")
    promote_parser.add_argument("--run", default="latest")
    promote_parser.add_argument("--name", default="main")
    promote_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    compare_parser = baseline_subparsers.add_parser("compare", help="Compare a run with a baseline.")
    compare_parser.add_argument("--run", default="latest")
    compare_parser.add_argument("--baseline", default="main")
    compare_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)

    gate_parser = subparsers.add_parser("gate", help="Fail CI when eval quality is below threshold.")
    gate_parser.add_argument("--run", default="latest")
    gate_parser.add_argument("--baseline", default=None)
    gate_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    gate_parser.add_argument("--min-pass-rate", type=float, default=0.9)
    gate_parser.add_argument("--max-regression", type=float, default=0.02)
    gate_parser.add_argument("--max-error-rate", type=float, default=0.1)
    gate_parser.add_argument("--min-avg-score", type=float, default=0.0)

    trace_parser = subparsers.add_parser("trace", help="Print a debug trace by trace id.")
    trace_parser.add_argument("--run", default="latest")
    trace_parser.add_argument("--trace-id", required=True)
    trace_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)

    calibrate_parser = subparsers.add_parser("calibrate", help="Compare judge scores against human labels.")
    calibrate_parser.add_argument("--run", default="latest")
    calibrate_parser.add_argument("--labels", type=Path, required=True)
    calibrate_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    calibrate_parser.add_argument("--tolerance", type=float, default=0.15)

    monitor_parser = subparsers.add_parser("monitor", help="Continuously run an eval suite and alert on pass-rate drops.")
    monitor_parser.add_argument("--suite", default="sample")
    monitor_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    monitor_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    monitor_parser.add_argument("--interval-seconds", type=int, default=60)
    monitor_parser.add_argument("--iterations", type=int, default=1)
    monitor_parser.add_argument("--min-pass-rate", type=float, default=0.9)
    monitor_parser.add_argument("--webhook-url", default="")
    monitor_parser.add_argument("--agent", action="append", default=None)

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
        run_dir = run_suite(agents, cases, args.runs_dir, args.run_id, args.approve_dangerous, args.judge_command)
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

    if args.command == "baseline":
        run_id = _resolve_run_id(args.runs_dir, args.run)
        if args.baseline_command == "promote":
            path = promote_baseline(args.runs_dir, run_id, args.name)
            print(f"Promoted {run_id} to baseline {args.name}: {path}")
            return 0
        if args.baseline_command == "compare":
            current = load_summary(args.runs_dir / run_id / "summary.json")
            baseline = load_summary(args.runs_dir / "baselines" / f"{args.baseline}.json")
            print(json.dumps(compare_to_baseline(current, baseline), indent=2))
            return 0

    if args.command == "gate":
        run_id = _resolve_run_id(args.runs_dir, args.run)
        passed, report = evaluate_gate(
            args.runs_dir,
            run_id,
            args.baseline,
            args.min_pass_rate,
            args.max_regression,
            args.max_error_rate,
            args.min_avg_score,
        )
        print(json.dumps(report, indent=2))
        return 0 if passed else 1

    if args.command == "trace":
        run_id = _resolve_run_id(args.runs_dir, args.run)
        path = resolve_trace_path(args.runs_dir, run_id, args.trace_id)
        print(path.read_text(encoding="utf-8"))
        return 0

    if args.command == "calibrate":
        run_id = _resolve_run_id(args.runs_dir, args.run)
        report = calibrate_judge(args.runs_dir / run_id / "results.jsonl", args.labels, args.tolerance)
        output_path = args.runs_dir / run_id / "calibration.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "monitor":
        agents = _select_agents(load_agent_registry(args.config), args.agent)
        cases = load_suite(DEFAULT_EVAL_DIR / f"{args.suite}.jsonl")
        snapshots = run_monitor(
            agents,
            cases,
            args.runs_dir,
            args.interval_seconds,
            args.iterations,
            args.min_pass_rate,
            args.webhook_url,
        )
        print(json.dumps(snapshots, indent=2))
        return 1 if any(snapshot["alert"] for snapshot in snapshots) else 0

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
