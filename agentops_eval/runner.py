from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .adapters import run_agent_adapter
from .checks import validate_output
from .judging import judge_output
from .models import AgentConfig, AgentRunResult, CheckResult, EvalCase
from .monitoring import EventWriter
from .reporting import write_debug_report, write_summary
from .tracing import make_trace_id, write_trace


def run_suite(
    agents: list[AgentConfig],
    cases: list[EvalCase],
    output_root: Path,
    run_id: str | None = None,
    approve_dangerous: bool = False,
    judge_command: str = "",
) -> Path:
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    events = EventWriter(run_dir / "events.jsonl")
    results_path = run_dir / "results.jsonl"

    events.emit("run_started", run_id=run_id, agents=[agent.name for agent in agents], case_count=len(cases))
    results: list[AgentRunResult] = []

    with results_path.open("w", encoding="utf-8") as result_file:
        for case in cases:
            for agent in agents:
                result = run_agent_case(run_id, run_dir, agent, case, events, approve_dangerous, judge_command)
                results.append(result)
                result_file.write(json.dumps(result.to_record(), ensure_ascii=True) + "\n")

    summary = write_summary(run_dir / "summary.json", results)
    write_debug_report(run_dir / "debug.md", results)
    events.emit("run_finished", run_id=run_id, passed=summary["passed"], pass_rate=summary["pass_rate"])
    (output_root / "latest.txt").write_text(run_id, encoding="utf-8")
    return run_dir


def run_agent_case(
    run_id: str,
    run_dir: Path,
    agent: AgentConfig,
    case: EvalCase,
    events: EventWriter,
    approve_dangerous: bool = False,
    judge_command: str = "",
) -> AgentRunResult:
    trace_id = make_trace_id(run_id, agent.name, case.case_id)
    events.emit("case_started", run_id=run_id, trace_id=trace_id, agent=agent.name, case_id=case.case_id)
    start = time.perf_counter()
    command_result = run_agent_adapter(agent, case, approve_dangerous)

    latency_ms = int((time.perf_counter() - start) * 1000)
    checks = validate_output(case, command_result.stdout) if not command_result.timed_out and command_result.exit_code == 0 else []
    judge_result = judge_output(case, command_result.stdout, judge_command) if not command_result.timed_out and command_result.exit_code == 0 else None
    if judge_result is not None:
        checks.append(
            CheckResult(
                name="rubric_score",
                passed=judge_result.score >= case.checks.min_score,
                detail=judge_result.reasoning,
                score=judge_result.score,
            )
        )
    passed = bool(checks) and all(check.passed for check in checks) and not command_result.timed_out and command_result.exit_code == 0

    result = AgentRunResult(
        trace_id=trace_id,
        run_id=run_id,
        agent=agent.name,
        case_id=case.case_id,
        passed=passed,
        latency_ms=latency_ms,
        timed_out=command_result.timed_out,
        exit_code=command_result.exit_code,
        stdout=command_result.stdout,
        stderr=command_result.stderr,
        checks=checks,
        error_type=command_result.error_type,
        score=judge_result.score if judge_result else None,
        judge_reasoning=judge_result.reasoning if judge_result else "",
        judge_mode=judge_result.mode if judge_result else "none",
    )
    trace_path = write_trace(run_dir, agent, case, result)
    events.emit(
        "case_finished",
        run_id=run_id,
        trace_id=trace_id,
        agent=agent.name,
        case_id=case.case_id,
        passed=passed,
        latency_ms=latency_ms,
        error_type=command_result.error_type,
        trace_path=str(trace_path),
    )
    return result
