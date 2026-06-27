from __future__ import annotations

import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .checks import validate_output
from .models import AgentConfig, AgentRunResult, EvalCase
from .monitoring import EventWriter
from .reporting import write_debug_report, write_summary


def run_suite(
    agents: list[AgentConfig],
    cases: list[EvalCase],
    output_root: Path,
    run_id: str | None = None,
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
                result = run_agent_case(run_id, agent, case, events)
                results.append(result)
                result_file.write(json.dumps(result.to_record(), ensure_ascii=True) + "\n")

    summary = write_summary(run_dir / "summary.json", results)
    write_debug_report(run_dir / "debug.md", results)
    events.emit("run_finished", run_id=run_id, passed=summary["passed"], pass_rate=summary["pass_rate"])
    (output_root / "latest.txt").write_text(run_id, encoding="utf-8")
    return run_dir


def run_agent_case(
    run_id: str,
    agent: AgentConfig,
    case: EvalCase,
    events: EventWriter,
) -> AgentRunResult:
    events.emit("case_started", run_id=run_id, agent=agent.name, case_id=case.case_id)
    start = time.perf_counter()
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    error_type: str | None = None

    try:
        completed = subprocess.run(
            shlex.split(agent.command),
            input=case.input_text,
            text=True,
            capture_output=True,
            timeout=agent.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        exit_code = completed.returncode
        if completed.returncode != 0:
            error_type = "non_zero_exit"
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        error_type = "timeout"
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
    except OSError as exc:
        error_type = "command_error"
        stderr = str(exc)

    latency_ms = int((time.perf_counter() - start) * 1000)
    checks = validate_output(case, stdout) if not timed_out and exit_code == 0 else []
    passed = bool(checks) and all(check.passed for check in checks) and not timed_out and exit_code == 0

    result = AgentRunResult(
        run_id=run_id,
        agent=agent.name,
        case_id=case.case_id,
        passed=passed,
        latency_ms=latency_ms,
        timed_out=timed_out,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        checks=checks,
        error_type=error_type,
    )
    events.emit(
        "case_finished",
        run_id=run_id,
        agent=agent.name,
        case_id=case.case_id,
        passed=passed,
        latency_ms=latency_ms,
        error_type=error_type,
    )
    return result
