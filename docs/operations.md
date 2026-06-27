# Operations Guide

## Monitoring Signals

Every evaluation run writes `events.jsonl` with these event types:

- `run_started`: run id, selected agents, and case count.
- `case_started`: agent and case id at the input boundary.
- `case_finished`: pass/fail, latency, timeout, and error type.
- `run_finished`: final pass count and pass rate.

Every case also writes a trace file under `runs/<run-id>/traces/<agent>/<case>.json`. The trace carries the input, checks, command adapter settings, output, stderr, latency, and `trace_id`.

Recommended dashboards:

- Pass rate by agent and suite.
- Failure count by `error_type`.
- p95 latency by agent.
- Timeout count by agent.
- Safety failure count by tag.

Recommended alerts:

- Any safety-tagged case fails.
- Timeout rate exceeds 1% in a release gate.
- Infrastructure failure rate exceeds 5%.
- Pass rate drops by more than 2 percentage points from baseline.

Use the built-in monitor command for local or scheduled smoke checks:

```powershell
python -m agentops_eval.cli monitor --suite sample --iterations 5 --interval-seconds 60 --min-pass-rate 0.95
```

## Debugging Workflow

1. Open `runs/<run-id>/summary.json` to identify the failing agent.
2. Open `runs/<run-id>/debug.md` to inspect failure clusters.
3. Copy the failed case `trace_id`.
4. Run `python -m agentops_eval.cli trace --run <run-id> --trace-id <trace-id>`.
5. Reproduce one failing agent/case pair only.
6. Inspect the input/output boundary before changing prompts or code.
7. Classify the root cause as config, prompt, model behavior, tool failure, timeout, or eval-case issue.
8. Add or update an eval case after the root cause is fixed.

Do not patch the evaluated agent from this platform automatically. The platform should produce evidence and recommended next actions; a human approves agent changes.

## Real Agent Adapter Contract

The first version uses command adapters:

- Input: full eval prompt on `stdin`.
- Output: final answer on `stdout`.
- Errors: diagnostics on `stderr`.
- Exit code: `0` for successful agent execution, non-zero for infrastructure/runtime failure.
- Timeout: enforced per agent from `configs/agents.yaml`.

If an existing agent needs HTTP, SDK, or queue invocation, add a small command wrapper that preserves this contract. That keeps the evaluation runner stable while the integration details change outside it.

The repository includes a built-in HTTP wrapper:

```powershell
python -m agentops_eval.http_agent --url http://localhost:8080/invoke --output-field answer
```

See `docs/adapters.md` for examples.

## Regression Baselines and CI Gate

Promote a known-good run:

```powershell
python -m agentops_eval.cli baseline promote --run latest --name main
```

Gate the current run against thresholds:

```powershell
python -m agentops_eval.cli gate --run latest --baseline main --min-pass-rate 0.95 --max-regression 0.02 --max-error-rate 0.05
```

The gate writes `runs/<run-id>/gate.json` and exits non-zero on failure, which makes it suitable for CI. GitHub Actions runs unit tests, the sample smoke suite, and the gate on pull requests.

## Artifact Hygiene

- Do not store secrets or raw production personal data in eval cases.
- Redact logs before adding real failures to `evals/`.
- Keep long raw traces out of git unless they are anonymized fixtures.
- Promote only stable, reviewed cases from smoke suites into release gates.
