# AgentOps-Eval-Platform

AgentOps-Eval-Platform is a local-first evaluation, monitoring, and debugging agent for existing AI agents.

It runs shared test cases against each agent, validates outputs with deterministic checks and rubric rules, writes structured telemetry, and produces failure reports that are useful for prompt, tool, and runtime debugging.

## Quick Start

```powershell
python -m agentops_eval.cli init
python -m agentops_eval.cli list-agents
python -m agentops_eval.cli run --suite sample
python -m agentops_eval.cli report --run latest
python -m agentops_eval.cli gate --run latest --min-pass-rate 0.90
```

The default registry uses mock command agents so the platform works immediately. Replace each command in `configs/agents.yaml` with commands that invoke your real agents. You can register one agent or many agents.

## Connect Existing Agents

Each agent command receives the eval input on `stdin` and should print its final answer on `stdout`.

Example command shape:

```yaml
agents:
  planner:
    command: "python path/to/planner_agent.py"
    timeout_seconds: 30
  researcher:
    command: "python path/to/researcher_agent.py"
    timeout_seconds: 45
  executor:
    command: "python path/to/executor_agent.py"
    timeout_seconds: 60
```

Run all registered agents:

```powershell
python -m agentops_eval.cli run --suite sample
```

Run a subset:

```powershell
python -m agentops_eval.cli run --suite sample --agent planner --agent executor
```

## Hard Capabilities

### Real Agent Integration

Use `configs/agents.yaml` to register command adapters for real agents. The platform captures `stdout`, `stderr`, exit code, timeout status, latency, and a per-case trace.

HTTP agents can use the bundled wrapper:

```yaml
agents:
  support_agent:
    command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --output-field answer"
    timeout_seconds: 30
```

See `docs/adapters.md` for CLI, HTTP, SDK, and queue adapter patterns.

### Debug Trace

Every run writes traces under `runs/<run-id>/traces/<agent>/<case>.json`. Failed cases also show their `trace_id` in `debug.md`.

```powershell
python -m agentops_eval.cli trace --run latest --trace-id <trace-id>
```

### Regression Baseline

Promote a known-good run:

```powershell
python -m agentops_eval.cli baseline promote --run latest --name main
```

Compare later runs:

```powershell
python -m agentops_eval.cli baseline compare --run latest --baseline main
```

### CI Gate

Fail builds when pass rate, error rate, or regression thresholds are exceeded:

```powershell
python -m agentops_eval.cli gate --run latest --baseline main --min-pass-rate 0.95 --max-regression 0.02
```

GitHub Actions is configured in `.github/workflows/agentops-eval.yml`.

### Continuous Monitoring

Run repeated smoke evals and return non-zero when the pass rate drops below threshold:

```powershell
python -m agentops_eval.cli monitor --suite sample --iterations 5 --interval-seconds 60 --min-pass-rate 0.95
```

## Repository Layout

- `agentops_eval/`: evaluation runner, checks, monitoring events, debugging report generation.
- `configs/agents.yaml`: agent registry.
- `evals/sample.jsonl`: starter eval cases.
- `docs/agent-spec.md`: authority, tool gates, loop, memory, escalation, and failure handling.
- `docs/adapters.md`: real agent adapter contract and HTTP wrapper.
- `docs/eval-plan.md`: metrics, rubric, baselines, pass bars, and regression gate.
- `docs/operations.md`: monitoring signals, alerts, and debugging workflow.
- `runs/`: generated run artifacts.

## Verify

```powershell
python -m unittest discover
python -m agentops_eval.cli run --suite sample
```

## Output Artifacts

Each run creates:

- `results.jsonl`: one result per agent per case.
- `events.jsonl`: structured monitoring events.
- `traces/`: per-agent, per-case debug traces.
- `debug.md`: grouped failure analysis and next actions.
- `summary.json`: suite-level pass/fail summary.
