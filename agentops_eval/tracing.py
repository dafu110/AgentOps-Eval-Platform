from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AgentConfig, AgentRunResult, EvalCase


def make_trace_id(run_id: str, agent_name: str, case_id: str) -> str:
    raw = f"{run_id}:{agent_name}:{case_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def write_trace(
    run_dir: Path,
    agent: AgentConfig,
    case: EvalCase,
    result: AgentRunResult,
) -> Path:
    trace_dir = run_dir / "traces" / agent.name
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{case.case_id}.json"
    payload: dict[str, Any] = {
        "trace_id": result.trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": result.run_id,
        "agent": {
            "name": agent.name,
            "command": agent.command,
            "timeout_seconds": agent.timeout_seconds,
        },
        "case": {
            "id": case.case_id,
            "input": case.input_text,
            "tags": list(case.tags),
            "checks": {
                "contains": list(case.checks.contains),
                "not_contains": list(case.checks.not_contains),
                "min_length": case.checks.min_length,
                "expect_json": case.checks.expect_json,
                "json_fields": list(case.checks.json_fields),
            },
        },
        "result": result.to_record(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def resolve_trace_path(runs_dir: Path, run_id: str, trace_id: str) -> Path:
    run_dir = runs_dir / run_id
    for path in (run_dir / "traces").glob("*/*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("trace_id") == trace_id:
            return path
    raise FileNotFoundError(f"Trace id {trace_id} not found in {run_dir}")
