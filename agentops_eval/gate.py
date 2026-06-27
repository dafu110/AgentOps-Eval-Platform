from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline import compare_to_baseline, load_summary


def evaluate_gate(
    runs_dir: Path,
    run_id: str,
    baseline_name: str | None,
    min_pass_rate: float,
    max_regression: float,
    max_error_rate: float,
) -> tuple[bool, dict[str, Any]]:
    current_path = runs_dir / run_id / "summary.json"
    current = load_summary(current_path)
    total = int(current.get("total", 0))
    failed = int(current.get("failed", 0))
    pass_rate = float(current.get("pass_rate", 0))
    error_rate = round(failed / total, 4) if total else 1.0

    checks: list[dict[str, Any]] = [
        {
            "name": "min_pass_rate",
            "passed": pass_rate >= min_pass_rate,
            "actual": pass_rate,
            "threshold": min_pass_rate,
        },
        {
            "name": "max_error_rate",
            "passed": error_rate <= max_error_rate,
            "actual": error_rate,
            "threshold": max_error_rate,
        },
    ]

    baseline_comparison = None
    if baseline_name:
        baseline_path = runs_dir / "baselines" / f"{baseline_name}.json"
        baseline_comparison = compare_to_baseline(current, load_summary(baseline_path))
        checks.append(
            {
                "name": "max_regression",
                "passed": baseline_comparison["pass_rate_delta"] >= -max_regression,
                "actual": baseline_comparison["pass_rate_delta"],
                "threshold": -max_regression,
            }
        )

    passed = all(check["passed"] for check in checks)
    report = {
        "run_id": run_id,
        "passed": passed,
        "checks": checks,
        "baseline": baseline_name,
        "baseline_comparison": baseline_comparison,
    }
    (runs_dir / run_id / "gate.json").write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    return passed, report
