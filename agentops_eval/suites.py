from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EvalCase, EvalChecks


class SuiteError(ValueError):
    pass


def load_suite(path: Path) -> list[EvalCase]:
    if not path.exists():
        raise SuiteError(f"Eval suite not found: {path}")

    cases: list[EvalCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SuiteError(f"Invalid JSON on line {line_number}: {exc}") from exc
        cases.append(_case_from_record(record, line_number))

    if not cases:
        raise SuiteError(f"Eval suite is empty: {path}")
    return cases


def _case_from_record(record: dict[str, Any], line_number: int) -> EvalCase:
    case_id = str(record.get("id", "")).strip()
    input_text = str(record.get("input", ""))
    if not case_id:
        raise SuiteError(f"Line {line_number} is missing id")
    if not input_text:
        raise SuiteError(f"Line {line_number} is missing input")

    checks_record = record.get("checks", {})
    if not isinstance(checks_record, dict):
        raise SuiteError(f"Line {line_number} checks must be an object")

    checks = EvalChecks(
        contains=tuple(_string_list(checks_record.get("contains", []), "contains", line_number)),
        not_contains=tuple(_string_list(checks_record.get("not_contains", []), "not_contains", line_number)),
        min_length=int(checks_record.get("min_length", 1)),
        expect_json=bool(checks_record.get("expect_json", False)),
        json_fields=tuple(_string_list(checks_record.get("json_fields", []), "json_fields", line_number)),
    )
    tags = tuple(_string_list(record.get("tags", []), "tags", line_number))
    return EvalCase(case_id=case_id, input_text=input_text, checks=checks, tags=tags)


def _string_list(value: Any, field: str, line_number: int) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SuiteError(f"Line {line_number} field {field} must be a list of strings")
    return value
