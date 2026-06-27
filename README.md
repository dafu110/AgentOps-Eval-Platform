# AgentOps-Eval-Platform

AgentOps-Eval-Platform is a local-first evaluation, monitoring, and debugging agent for three existing agents.

It runs shared test cases against each agent, validates outputs with deterministic checks and rubric rules, writes structured telemetry, and produces failure reports that are useful for prompt, tool, and runtime debugging.

## Quick Start

```powershell
python -m agentops_eval.cli init
python -m agentops_eval.cli list-agents
python -m agentops_eval.cli run --suite sample
python -m agentops_eval.cli report --run latest
```

The default registry uses mock command agents so the platform works immediately. Replace each command in `configs/agents.yaml` with the command that invokes your real agents.

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

## Repository Layout

- `agentops_eval/`: evaluation runner, checks, monitoring events, debugging report generation.
- `configs/agents.yaml`: three-agent registry.
- `evals/sample.jsonl`: starter eval cases.
- `docs/agent-spec.md`: authority, tool gates, loop, memory, escalation, and failure handling.
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
- `debug.md`: grouped failure analysis and next actions.
- `summary.json`: suite-level pass/fail summary.
