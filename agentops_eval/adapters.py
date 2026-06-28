from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import AgentConfig, EvalCase
from .security import build_sandbox_env, redact_secrets, validate_command_policy

SUPPORTED_ADAPTERS = {
    "command",
    "http-json",
    "agentflow-http",
    "bigdata-http",
}


@dataclass(frozen=True)
class AgentCommandResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    error_type: str | None


def run_agent_adapter(agent: AgentConfig, case: EvalCase, approve_dangerous: bool = False) -> AgentCommandResult:
    """Dispatch an eval case through the adapter named in agent config."""
    adapter = agent.adapter.strip().lower() or "command"
    if adapter not in SUPPORTED_ADAPTERS:
        supported = ", ".join(sorted(SUPPORTED_ADAPTERS))
        return AgentCommandResult(
            stdout="",
            stderr=f"Unsupported adapter {agent.adapter!r}; supported adapters: {supported}",
            exit_code=None,
            timed_out=False,
            error_type="unsupported_adapter",
        )
    return run_command_agent(agent, case, approve_dangerous)


def run_command_agent(agent: AgentConfig, case: EvalCase, approve_dangerous: bool = False) -> AgentCommandResult:
    """Invoke a real agent through the command adapter contract."""
    stdout = ""
    stderr = ""
    exit_code: int | None = None
    timed_out = False
    error_type: str | None = None

    try:
        command = validate_command_policy(agent, approve_dangerous)
        completed = subprocess.run(
            command,
            input=case.input_text,
            text=True,
            capture_output=True,
            timeout=agent.timeout_seconds,
            check=False,
            cwd=agent.cwd or None,
            env=build_sandbox_env(agent),
        )
        stdout = redact_secrets(completed.stdout.strip())
        stderr = redact_secrets(completed.stderr.strip())
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
        stderr = redact_secrets(str(exc))
    except PermissionError as exc:
        error_type = "security_policy"
        stderr = redact_secrets(str(exc))

    return AgentCommandResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        error_type=error_type,
    )
