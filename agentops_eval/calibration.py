from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def calibrate_judge(results_path: Path, labels_path: Path, tolerance: float = 0.15) -> dict[str, Any]:
    results = _load_results(results_path)
    labels = _load_labels(labels_path)
    compared = []
    for key, human_score in labels.items():
        result = results.get(key)
        if not result or result.get("score") is None:
            continue
        judge_score = float(result["score"])
        delta = round(judge_score - human_score, 4)
        compared.append(
            {
                "key": key,
                "judge_score": judge_score,
                "human_score": human_score,
                "delta": delta,
                "within_tolerance": abs(delta) <= tolerance,
            }
        )
    agreement = (
        sum(1 for item in compared if item["within_tolerance"]) / len(compared)
        if compared
        else 0.0
    )
    return {
        "compared": len(compared),
        "agreement_rate": round(agreement, 4),
        "tolerance": tolerance,
        "items": compared,
    }


def _load_results(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        rows[f"{record['agent']}::{record['case_id']}"] = record
    return rows


def _load_labels(path: Path) -> dict[str, float]:
    labels: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        labels[f"{record['agent']}::{record['case_id']}"] = float(record["human_score"])
    return labels
