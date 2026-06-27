from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .models import AgentRunResult


def write_summary(path: Path, results: list[AgentRunResult]) -> dict[str, Any]:
    total = len(results)
    passed_count = sum(1 for result in results if result.passed)
    by_agent: dict[str, dict[str, Any]] = {}

    for agent in sorted({result.agent for result in results}):
        agent_results = [result for result in results if result.agent == agent]
        agent_passed = sum(1 for result in agent_results if result.passed)
        by_agent[agent] = {
            "total": len(agent_results),
            "passed": agent_passed,
            "failed": len(agent_results) - agent_passed,
            "pass_rate": round(agent_passed / len(agent_results), 4) if agent_results else 0,
            "p95_latency_ms": _percentile([result.latency_ms for result in agent_results], 95),
        }

    summary = {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "pass_rate": round(passed_count / total, 4) if total else 0,
        "by_agent": by_agent,
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    return summary


def write_debug_report(path: Path, results: list[AgentRunResult]) -> None:
    failures = [result for result in results if not result.passed]
    lines = ["# Debug Report", ""]
    lines.append(f"Total failures: {len(failures)}")
    lines.append("")

    if not failures:
        lines.append("All evaluated cases passed.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    by_agent: dict[str, list[AgentRunResult]] = defaultdict(list)
    for failure in failures:
        by_agent[failure.agent].append(failure)

    lines.append("## Failure Clusters")
    lines.append("")
    error_counts = Counter(failure.error_type or "check_failed" for failure in failures)
    for error_type, count in error_counts.most_common():
        lines.append(f"- `{error_type}`: {count}")
    lines.append("")

    for agent, agent_failures in sorted(by_agent.items()):
        lines.append(f"## Agent: {agent}")
        lines.append("")
        for failure in agent_failures:
            lines.append(f"### Case: {failure.case_id}")
            lines.append("")
            lines.append(f"- Error type: `{failure.error_type or 'check_failed'}`")
            lines.append(f"- Trace id: `{failure.trace_id}`")
            lines.append(f"- Exit code: `{failure.exit_code}`")
            lines.append(f"- Latency: `{failure.latency_ms}ms`")
            failed_checks = [check for check in failure.checks if not check.passed]
            if failed_checks:
                lines.append("- Failed checks:")
                for check in failed_checks:
                    lines.append(f"  - `{check.name}`: {check.detail}")
            if failure.stderr:
                lines.append(f"- Stderr: `{failure.stderr[:500]}`")
            lines.append("")
            lines.append("Suggested next action: reproduce this single case, inspect the agent input/output boundary, then update prompt/tooling only after the root cause is known.")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _percentile(values: list[int], percentile: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((percentile / 100) * (len(ordered) - 1))
    return ordered[index]
