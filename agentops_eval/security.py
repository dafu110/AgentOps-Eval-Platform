from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from .models import AgentConfig


class SecurityPolicyError(PermissionError):
    pass


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,}]+"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._-]+"),
]

DANGEROUS_TOKENS = {
    "rm",
    "del",
    "erase",
    "format",
    "shutdown",
    "reboot",
    "curl",
    "wget",
    "scp",
    "ssh",
    "powershell",
    "pwsh",
    "cmd",
}

ALLOWED_EXECUTABLES = {"python", "python3", "py"}


def validate_command_policy(agent: AgentConfig, approve_dangerous: bool = False) -> list[str]:
    parts = shlex.split(agent.command)
    if not parts:
        raise SecurityPolicyError(f"Agent {agent.name} has empty command")

    executable = Path(parts[0]).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]
    if executable not in ALLOWED_EXECUTABLES:
        raise SecurityPolicyError(f"Agent {agent.name} executable {parts[0]!r} is not allowlisted")

    dangerous = sorted({part.lower() for part in parts if part.lower() in DANGEROUS_TOKENS})
    if dangerous and not approve_dangerous:
        joined = ", ".join(dangerous)
        raise SecurityPolicyError(f"Agent {agent.name} command contains dangerous token(s): {joined}")

    if agent.requires_approval and not approve_dangerous:
        raise SecurityPolicyError(f"Agent {agent.name} requires explicit approval before execution")

    if agent.danger_level.lower() in {"high", "critical"} and not approve_dangerous:
        raise SecurityPolicyError(f"Agent {agent.name} danger_level={agent.danger_level} requires approval")

    return parts


def build_sandbox_env(agent: AgentConfig) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    for key in agent.env_allowlist:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_redaction, redacted)
    return redacted


def _redaction(match: re.Match[str]) -> str:
    value = match.group(0)
    if value.lower().startswith("authorization:"):
        return match.group(1) + "[REDACTED]"
    key = value.split("=", 1)[0].split(":", 1)[0]
    if key != value:
        separator = "=" if "=" in value else ":"
        return f"{key}{separator}[REDACTED]"
    return "[REDACTED]"
