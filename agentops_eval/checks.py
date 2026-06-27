from __future__ import annotations

import json

from .models import CheckResult, EvalCase


def validate_output(case: EvalCase, output: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    normalized = output.lower()

    checks.append(
        CheckResult(
            name="min_length",
            passed=len(output.strip()) >= case.checks.min_length,
            detail=f"length={len(output.strip())}, required={case.checks.min_length}",
        )
    )

    for expected in case.checks.contains:
        checks.append(
            CheckResult(
                name=f"contains:{expected}",
                passed=expected.lower() in normalized,
                detail=f"expected substring {expected!r}",
            )
        )

    for forbidden in case.checks.not_contains:
        checks.append(
            CheckResult(
                name=f"not_contains:{forbidden}",
                passed=forbidden.lower() not in normalized,
                detail=f"forbidden substring {forbidden!r}",
            )
        )

    parsed_json: object | None = None
    if case.checks.expect_json:
        try:
            parsed_json = json.loads(output)
            checks.append(CheckResult(name="valid_json", passed=True, detail="output parses as JSON"))
        except json.JSONDecodeError as exc:
            checks.append(CheckResult(name="valid_json", passed=False, detail=str(exc)))

    for field in case.checks.json_fields:
        passed = isinstance(parsed_json, dict) and field in parsed_json
        checks.append(
            CheckResult(
                name=f"json_field:{field}",
                passed=passed,
                detail=f"required JSON field {field!r}",
            )
        )

    if case.checks.rubric:
        checks.append(
            CheckResult(
                name="rubric_present",
                passed=True,
                detail=case.checks.rubric,
            )
        )

    return checks
