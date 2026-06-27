from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass

from .models import AgentConfig, EvalCase


@dataclass(frozen=True)
class AgentCommandResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    error_type: str | None


def run_command_agent(agent: AgentConfig, case: EvalCase) -> AgentCommandResult:
    """Invoke a real agent through the command adapter contract."""
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

    return AgentCommandResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        error_type=error_type,
    )
