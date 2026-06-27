from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def promote_baseline(runs_dir: Path, run_id: str, baseline_name: str) -> Path:
    source = runs_dir / run_id / "summary.json"
    if not source.exists():
        raise FileNotFoundError(f"Run summary not found: {source}")

    baseline_dir = runs_dir / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    target = baseline_dir / f"{baseline_name}.json"
    shutil.copyfile(source, target)
    return target


def load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Summary not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compare_to_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    current_rate = float(current.get("pass_rate", 0))
    baseline_rate = float(baseline.get("pass_rate", 0))
    by_agent: dict[str, Any] = {}

    baseline_agents = baseline.get("by_agent", {})
    current_agents = current.get("by_agent", {})
    for agent in sorted(set(baseline_agents) | set(current_agents)):
        current_agent = current_agents.get(agent, {})
        baseline_agent = baseline_agents.get(agent, {})
        by_agent[agent] = {
            "current_pass_rate": float(current_agent.get("pass_rate", 0)),
            "baseline_pass_rate": float(baseline_agent.get("pass_rate", 0)),
            "pass_rate_delta": round(
                float(current_agent.get("pass_rate", 0)) - float(baseline_agent.get("pass_rate", 0)),
                4,
            ),
            "current_p95_latency_ms": int(current_agent.get("p95_latency_ms", 0)),
            "baseline_p95_latency_ms": int(baseline_agent.get("p95_latency_ms", 0)),
        }

    return {
        "current_pass_rate": current_rate,
        "baseline_pass_rate": baseline_rate,
        "pass_rate_delta": round(current_rate - baseline_rate, 4),
        "by_agent": by_agent,
    }
