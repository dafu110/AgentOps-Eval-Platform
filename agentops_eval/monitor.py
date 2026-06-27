from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .models import AgentConfig, EvalCase
from .runner import run_suite


def run_monitor(
    agents: list[AgentConfig],
    cases: list[EvalCase],
    runs_dir: Path,
    interval_seconds: int,
    iterations: int,
    min_pass_rate: float,
) -> list[dict[str, Any]]:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    snapshots: list[dict[str, Any]] = []
    for index in range(iterations):
        run_id = f"monitor-{int(time.time())}-{index + 1}"
        run_dir = run_suite(agents, cases, runs_dir, run_id)
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        snapshot = {
            "run_id": run_id,
            "pass_rate": summary["pass_rate"],
            "alert": summary["pass_rate"] < min_pass_rate,
            "threshold": min_pass_rate,
        }
        snapshots.append(snapshot)
        if index < iterations - 1:
            time.sleep(interval_seconds)
    return snapshots
