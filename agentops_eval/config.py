from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import AgentConfig
from .adapters import SUPPORTED_ADAPTERS


class ConfigError(ValueError):
    pass


def load_agent_registry(path: Path) -> list[AgentConfig]:
    """Load agent registry YAML, preferring PyYAML when available."""
    if not path.exists():
        raise ConfigError(f"Agent registry not found: {path}")

    _reject_duplicate_agent_blocks(path)
    loaded = _load_with_pyyaml(path)
    if loaded is not None:
        return _validate_agents(_agents_from_mapping(loaded, path), path)

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

    return _validate_agents(agents, path)


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
        adapter=mapping.get("adapter", "command"),
        repo_url=mapping.get("repo_url", ""),
        health_url=mapping.get("health_url", ""),
        cwd=mapping.get("cwd", ""),
        requires_approval=_as_bool(mapping.get("requires_approval", "false")),
        danger_level=mapping.get("danger_level", "low"),
        env_allowlist=tuple(_as_list(mapping.get("env_allowlist", ""))),
    )


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _reject_duplicate_agent_blocks(path: Path) -> None:
    names: list[str] = []
    in_agents = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line == "agents:":
            in_agents = True
            continue
        if not in_agents:
            continue
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            names.append(match.group(1))
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        joined = ", ".join(duplicate_names)
        raise ConfigError(f"Duplicate agent names in {path}: {joined}")


def _load_with_pyyaml(path: Path) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return None

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ConfigError(f"Agent registry root must be a mapping: {path}")
    return loaded


def _agents_from_mapping(loaded: dict[str, Any], path: Path) -> list[AgentConfig]:
    raw_agents = loaded.get("agents")
    if raw_agents is None:
        return []
    if not isinstance(raw_agents, dict):
        raise ConfigError(f"Agent registry must contain an agents mapping: {path}")

    agents: list[AgentConfig] = []
    for name, raw_mapping in raw_agents.items():
        if not isinstance(raw_mapping, dict):
            raise ConfigError(f"Agent {name} must be a mapping")
        mapping = {str(key): _stringify_value(value) for key, value in raw_mapping.items()}
        agents.append(_agent_from_mapping(str(name), mapping))
    return agents


def _validate_agents(agents: list[AgentConfig], path: Path) -> list[AgentConfig]:
    if not agents:
        raise ConfigError(f"Expected at least 1 agent in {path}")

    names = [agent.name for agent in agents]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        joined = ", ".join(duplicate_names)
        raise ConfigError(f"Duplicate agent names in {path}: {joined}")
    unsupported_adapters = sorted({agent.adapter for agent in agents if agent.adapter not in SUPPORTED_ADAPTERS})
    if unsupported_adapters:
        joined = ", ".join(unsupported_adapters)
        supported = ", ".join(sorted(SUPPORTED_ADAPTERS))
        raise ConfigError(f"Unsupported adapter(s) in {path}: {joined}. Supported: {supported}")
    return agents


def _stringify_value(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_list(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]
