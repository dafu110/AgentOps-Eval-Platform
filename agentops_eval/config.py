from __future__ import annotations

import re
from pathlib import Path

from .models import AgentConfig


class ConfigError(ValueError):
    pass


def load_agent_registry(path: Path) -> list[AgentConfig]:
    """Load a small YAML subset used by configs/agents.yaml."""
    if not path.exists():
        raise ConfigError(f"Agent registry not found: {path}")

    agents: list[AgentConfig] = []
    current_name: str | None = None
    current: dict[str, str] = {}
    in_agents = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line == "agents:":
            in_agents = True
            continue
        if not in_agents:
            continue

        name_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if name_match:
            if current_name is not None:
                agents.append(_agent_from_mapping(current_name, current))
            current_name = name_match.group(1)
            current = {}
            continue

        field_match = re.match(r"^    ([A-Za-z0-9_-]+):\s*(.*)$", line)
        if field_match and current_name is not None:
            key = field_match.group(1)
            value = field_match.group(2).strip()
            current[key] = _strip_quotes(value)

    if current_name is not None:
        agents.append(_agent_from_mapping(current_name, current))

    if not agents:
        raise ConfigError(f"Expected at least 1 agent in {path}")

    names = [agent.name for agent in agents]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        joined = ", ".join(duplicate_names)
        raise ConfigError(f"Duplicate agent names in {path}: {joined}")

    return agents


def _agent_from_mapping(name: str, mapping: dict[str, str]) -> AgentConfig:
    command = mapping.get("command", "").strip()
    if not command:
        raise ConfigError(f"Agent {name} is missing command")

    try:
        timeout = int(mapping.get("timeout_seconds", "30"))
    except ValueError as exc:
        raise ConfigError(f"Agent {name} has invalid timeout_seconds") from exc

    if timeout <= 0:
        raise ConfigError(f"Agent {name} timeout_seconds must be positive")

    return AgentConfig(
        name=name,
        command=command,
        timeout_seconds=timeout,
        description=mapping.get("description", ""),
    )


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
