from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass

from .models import EvalCase
from .security import redact_secrets


@dataclass(frozen=True)
class JudgeResult:
    score: float
    reasoning: str


def judge_output(case: EvalCase, output: str, judge_command: str = "") -> JudgeResult | None:
    if not case.checks.rubric:
        return None
    if judge_command:
        return _judge_with_command(case, output, judge_command)
    return _heuristic_judge(case, output)


def _heuristic_judge(case: EvalCase, output: str) -> JudgeResult:
    score = 1.0
    reasons: list[str] = []
    normalized = output.lower()
    if len(output.strip()) < case.checks.min_length:
        score -= 0.25
        reasons.append("output shorter than minimum length")
    for expected in case.checks.contains:
        if expected.lower() not in normalized:
            score -= 0.2
            reasons.append(f"missing required phrase {expected!r}")
    for forbidden in case.checks.not_contains:
        if forbidden.lower() in normalized:
            score -= 0.4
            reasons.append(f"contains forbidden phrase {forbidden!r}")
    if case.checks.expect_json:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            score -= 0.35
            reasons.append("output is not valid JSON")
        else:
            for field in case.checks.json_fields:
                if not isinstance(parsed, dict) or field not in parsed:
                    score -= 0.15
                    reasons.append(f"missing JSON field {field!r}")
    final_score = max(0.0, min(1.0, round(score, 4)))
    reasoning = "; ".join(reasons) if reasons else f"heuristic rubric passed: {case.checks.rubric}"
    return JudgeResult(score=final_score, reasoning=reasoning)


def _judge_with_command(case: EvalCase, output: str, judge_command: str) -> JudgeResult:
    payload = {
        "case_id": case.case_id,
        "input": case.input_text,
        "output": output,
        "rubric": case.checks.rubric,
    }
    completed = subprocess.run(
        shlex.split(judge_command),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return JudgeResult(score=0.0, reasoning=redact_secrets(completed.stderr.strip() or "judge command failed"))
    try:
        record = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return JudgeResult(score=0.0, reasoning="judge command returned invalid JSON")
    return JudgeResult(
        score=max(0.0, min(1.0, float(record.get("score", 0.0)))),
        reasoning=redact_secrets(str(record.get("reasoning", ""))),
    )
