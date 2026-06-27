from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .models import AgentConfig, EvalCase
from .runner import run_suite


def run_monitor(
    agents: list[AgentConfig],
    cases: list[EvalCase],
    runs_dir: Path,
    interval_seconds: int,
    iterations: int,
    min_pass_rate: float,
    webhook_url: str = "",
) -> list[dict[str, Any]]:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    snapshots: list[dict[str, Any]] = []
    for index in range(iterations):
        run_id = f"monitor-{int(time.time())}-{index + 1}"
        run_dir = run_suite(agents, cases, runs_dir, run_id)
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        snapshot = {
            "run_id": run_id,
            "pass_rate": summary["pass_rate"],
            "failed": summary["failed"],
            "total": summary["total"],
            "alert": summary["pass_rate"] < min_pass_rate,
            "threshold": min_pass_rate,
        }
        snapshots.append(snapshot)
        if snapshot["alert"] and webhook_url:
            send_webhook_alert(webhook_url, snapshot)
        if index < iterations - 1:
            time.sleep(interval_seconds)
    write_monitor_artifacts(runs_dir, snapshots)
    return snapshots


def write_monitor_artifacts(runs_dir: Path, snapshots: list[dict[str, Any]]) -> None:
    monitor_dir = runs_dir / "monitor"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    history_path = monitor_dir / "history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        for snapshot in snapshots:
            handle.write(json.dumps(snapshot, ensure_ascii=True) + "\n")
    (monitor_dir / "dashboard.html").write_text(render_dashboard(load_history(history_path)), encoding="utf-8")


def load_history(history_path: Path) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    return [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render_dashboard(history: list[dict[str, Any]]) -> str:
    points = "\n".join(
        f"<tr><td>{item['run_id']}</td><td>{item['pass_rate']:.4f}</td><td>{item['failed']}/{item['total']}</td><td>{item['alert']}</td></tr>"
        for item in history[-100:]
    )
    bars = "\n".join(
        f"<div class='bar' title='{item['run_id']}: {item['pass_rate']:.2f}' style='height:{max(2, int(item['pass_rate'] * 160))}px'></div>"
        for item in history[-50:]
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AgentOps Monitor</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #17202a; }}
    .chart {{ display: flex; align-items: end; gap: 4px; height: 180px; border-bottom: 1px solid #ccd; }}
    .bar {{ width: 14px; background: #2f80ed; }}
    table {{ border-collapse: collapse; margin-top: 24px; width: 100%; }}
    td, th {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
  </style>
</head>
<body>
  <h1>AgentOps Monitor</h1>
  <p>Recent pass-rate trend. Generated from local monitor snapshots.</p>
  <div class="chart">{bars}</div>
  <table><thead><tr><th>Run</th><th>Pass Rate</th><th>Failures</th><th>Alert</th></tr></thead><tbody>{points}</tbody></table>
</body>
</html>
"""


def send_webhook_alert(webhook_url: str, snapshot: dict[str, Any]) -> None:
    payload = json.dumps({"text": f"AgentOps alert: {snapshot['run_id']} pass_rate={snapshot['pass_rate']}"})
    request = Request(webhook_url, data=payload.encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10):
            return
    except URLError:
        return
