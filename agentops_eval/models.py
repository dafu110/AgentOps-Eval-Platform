from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentConfig:
    name: str
    command: str
    timeout_seconds: int = 30
    description: str = ""


@dataclass(frozen=True)
class EvalChecks:
    contains: tuple[str, ...] = ()
    not_contains: tuple[str, ...] = ()
    min_length: int = 1
    expect_json: bool = False
    json_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    input_text: str
    checks: EvalChecks
    tags: tuple[str, ...] = ()


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class AgentRunResult:
    run_id: str
    agent: str
    case_id: str
    passed: bool
    latency_ms: int
    timed_out: bool
    exit_code: int | None
    stdout: str
    stderr: str
    checks: list[CheckResult] = field(default_factory=list)
    error_type: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent": self.agent,
            "case_id": self.case_id,
            "passed": self.passed,
            "latency_ms": self.latency_ms,
            "timed_out": self.timed_out,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_type": self.error_type,
            "checks": [check.__dict__ for check in self.checks],
        }
