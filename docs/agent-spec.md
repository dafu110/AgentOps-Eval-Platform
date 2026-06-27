# Agent Spec: AgentOps-Eval-Platform

## 1. Goal & Scope

AgentOps-Eval-Platform evaluates, monitors, and debugs three existing agents by running repeatable eval suites, collecting structured execution telemetry, and producing actionable failure reports.

Non-goals:

- It does not autonomously modify the evaluated agents.
- It does not deploy agents or change production traffic.
- It does not send external notifications without explicit approval.
- It does not treat LLM-judge scores as the only quality signal.

Authority limits:

- Read eval cases, configs, run logs, and local artifacts.
- Execute configured agent commands inside a bounded run.
- Write local run artifacts and reports.
- Propose fixes, prompt changes, or investigation paths; human approval is required before changing the existing agents.

## 2. Tools / Actions

| Tool | Purpose | Reversible? | Gate |
|---|---|---:|---|
| `load_agent_registry` | Read the three-agent registry from config | yes | none |
| `load_eval_suite` | Read eval cases from JSONL | yes | none |
| `run_agent_command` | Execute a configured agent against one eval input | yes for eval side effects, unknown for agent internals | dry-run review for new commands; human approval for production-connected agents |
| `validate_output` | Run deterministic checks and rubric scoring | yes | none |
| `write_run_artifacts` | Persist local JSONL and Markdown reports | yes | none |
| `summarize_failures` | Group failures by agent, check, and likely root cause | yes | none |
| `modify_evaluated_agent` | Change code, prompts, or tool permissions for an existing agent | no | human approval required |
| `send_alert` | Notify a person or channel | no | human approval required |

## 3. Control Loop

1. Plan: select suite, agents, output directory, and budgets.
2. Act: run each case against each selected agent.
3. Observe: capture stdout, stderr, exit code, latency, timeout, and validation results.
4. Reflect: summarize pass rates, regressions, and failure clusters.
5. Stop: finish when all planned cases have run or a hard budget is reached.

Budgets:

- Max cases per invocation: 500 by default.
- Max agent runtime: per-agent `timeout_seconds`, default 30 seconds.
- Max total run time: 30 minutes unless explicitly overridden.
- Max retries: 1 retry for infrastructure errors; 0 retries for semantic failures.

## 4. Guardrails & Approval Gates

- Commands are allowlisted in `configs/agents.yaml`.
- Unknown or empty agent commands are rejected.
- Timeouts are mandatory for every agent.
- Output validation must run even when the command exits successfully.
- Production-connected, billing, messaging, deletion, or deployment-capable agents require human approval before evaluation runs.
- Any suggested code, prompt, policy, or tool-permission change is proposed as a report item, not applied automatically.

## 5. Memory & State

Task-local state:

- Active suite, run id, case inputs, agent outputs, validation scores, and telemetry events.

Durable state:

- Eval datasets in `evals/`.
- Agent registry in `configs/agents.yaml`.
- Generated run artifacts in `runs/<run-id>/`.
- Decisions and operating notes in `docs/`.

No secrets or raw production PII should be stored in eval cases or run artifacts.

## 6. Escalation & Handoff

Stop and ask a human when:

- A configured command has unclear side effects.
- More than 5% of cases fail due to infrastructure errors.
- An agent output appears to include secrets, credentials, or personal data.
- A fix requires modifying an evaluated agent.
- The same failure class repeats across three consecutive runs.
- The suite does not cover the behavior being judged.

## 7. Evaluation

Primary metrics:

- Case pass rate by agent and suite.
- Deterministic check pass rate.
- Rubric score average and minimum.
- Timeout/error rate.
- Regression delta from the latest baseline.
- Safety failure count.

Safety metric:

- Unauthorized action or unsafe content rate must be 0 for a passing release gate.

## 8. Failure Handling

- Tool errors are recorded as infrastructure failures with stderr and exit code.
- Timeouts produce a structured timeout result, not a partial pass.
- Invalid eval case schemas are rejected before the run starts.
- Missing expected fields fail fast with a clear message.
- On uncertainty, the platform stops and reports what is unknown instead of guessing.
