# AgentOps-Eval-Platform

AgentOps-Eval-Platform is a local-first evaluation, monitoring, and debugging agent for existing AI agents.

It runs shared test cases against each agent, validates outputs with deterministic checks and rubric rules, writes structured telemetry, and produces failure reports that are useful for prompt, tool, and runtime debugging.

## Quick Start

```powershell
python -m pip install -e .[dev]
agentops-eval init
agentops-eval list-agents
agentops-eval run --suite sample --config configs/agents.mock.yaml
agentops-eval report --run latest
agentops-eval gate --run latest --min-pass-rate 0.90
```

The default registry in `configs/agents.yaml` is wired to the three existing real agents:

- `peopleops-agent-platform`
- `Agent-Flow-Studio`
- `Big-Data-Analytics-Agent`

Use `configs/agents.mock.yaml` for CI and dependency-free smoke tests.

Real-agent runs require those services to be running on the configured local ports. If they are not running, the platform fails the run as an integration failure instead of silently falling back to mocks.

## Connect Existing Agents

Each agent command receives the eval input on `stdin` and should print its final answer on `stdout`.

Example command shape:

```yaml
agents:
  planner:
    adapter: command
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
agentops-eval run --suite sample
```

Run a subset:

```powershell
agentops-eval run --suite sample --agent planner --agent executor
```

## Hard Capabilities

### Real Agent Integration

Use `configs/agents.yaml` to register real agents. The platform captures `stdout`, `stderr`, exit code, timeout status, latency, rubric score, and a per-case trace.

HTTP agents can use the bundled wrapper:

```yaml
agents:
  support_agent:
    adapter: http-json
    command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --output-field answer"
    timeout_seconds: 30
```

The `adapter` field is validated and dispatched by the runner. Supported values are `command`, `http-json`, `agentflow-http`, and `bigdata-http`. See `docs/adapters.md` for CLI, HTTP, SDK, and queue adapter patterns.

The bundled real adapters cover:

- PeopleOps: generic HTTP JSON wrapper to `/chat`.
- AgentFlow: login/register plus `/api/generate-canvas`.
- BigData: multipart CSV upload to `/api/analyze`.

### Debug Trace

Every run writes traces under `runs/<run-id>/traces/<agent>/<case>.json`. Failed cases also show their `trace_id` in `debug.md`.

```powershell
agentops-eval trace --run latest --trace-id <trace-id>
```

### Regression Baseline

Promote a known-good run:

```powershell
agentops-eval baseline promote --run latest --name main
```

Compare later runs:

```powershell
agentops-eval baseline compare --run latest --baseline main
```

### CI Gate

Fail builds when pass rate, error rate, or regression thresholds are exceeded:

```powershell
agentops-eval gate --run latest --baseline main --min-pass-rate 0.95 --min-avg-score 0.80 --max-regression 0.02
```

GitHub Actions is configured in `.github/workflows/agentops-eval.yml`.

### Continuous Monitoring

Run repeated smoke evals and return non-zero when the pass rate drops below threshold:

```powershell
agentops-eval monitor --suite sample --iterations 5 --interval-seconds 60 --min-pass-rate 0.95 --webhook-url https://example.com/hook
```

The monitor writes `runs/monitor/history.jsonl` and `runs/monitor/dashboard.html`.

### Rubric Judge and Human Calibration

Eval cases can include `checks.rubric` and `checks.min_score`. By default the platform uses a deterministic heuristic judge; for LLM-as-judge, pass a judge command that reads JSON from `stdin` and returns `{"score": 0.0-1.0, "reasoning": "..."}`.

```powershell
agentops-eval run --suite sample --judge-command "python path/to/judge.py"
agentops-eval calibrate --run latest --labels evals/human_labels.sample.jsonl
agentops-eval gate --run latest --min-avg-score 0.85 --require-external-judge
```

Use the built-in heuristic judge for smoke checks only. Release gates should pass `--judge-command`, calibrate it against human labels, and add `--require-external-judge` so a heuristic-only run cannot accidentally ship.

### Command Safety

Agent commands are restricted to Python entrypoints by default. High-risk commands, dangerous shell tokens, or agents marked `requires_approval` need `--approve-dangerous`. Subprocess output is secret-redacted before it is written to run artifacts.

## Repository Layout

- `agentops_eval/`: evaluation runner, checks, monitoring events, debugging report generation.
- `configs/agents.yaml`: agent registry.
- `configs/agents.mock.yaml`: offline mock registry for CI and smoke tests.
- `evals/sample.jsonl`: 12-case starter suite covering smoke, JSON format, safety, ambiguity, monitoring, debugging, and release-gate slices.
- `docs/agent-spec.md`: authority, tool gates, loop, memory, escalation, and failure handling.
- `docs/adapters.md`: real agent adapter contract and HTTP wrapper.
- `docs/eval-plan.md`: metrics, rubric, baselines, pass bars, and regression gate.
- `docs/operations.md`: monitoring signals, alerts, and debugging workflow.
- `runs/`: generated run artifacts.

## Verify

```powershell
python -m unittest discover
agentops-eval run --suite sample --config configs/agents.mock.yaml
```

## Output Artifacts

Each run creates:

- `results.jsonl`: one result per agent per case.
- `events.jsonl`: structured monitoring events.
- `traces/`: per-agent, per-case debug traces.
- `debug.md`: grouped failure analysis and next actions.
- `summary.json`: suite-level pass/fail summary.
