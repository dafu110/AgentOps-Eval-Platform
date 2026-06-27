# Real Agent Adapters

AgentOps-Eval-Platform invokes real agents through small command adapters. This keeps the runner stable while each agent can be implemented as a CLI, HTTP service, SDK wrapper, or queue worker.

## Command Adapter Contract

- Input: eval prompt on `stdin`.
- Output: final answer on `stdout`.
- Diagnostics: logs and errors on `stderr`.
- Exit code: `0` means the agent ran successfully; non-zero means infrastructure/runtime failure.
- Timeout: enforced by the registry's `timeout_seconds`.

Example:

```yaml
agents:
  planner:
    command: "python path/to/planner_agent.py"
    timeout_seconds: 30
```

## Built-In HTTP Adapter

For HTTP agents, use the bundled wrapper:

```yaml
agents:
  support_agent:
    command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --output-field answer"
    timeout_seconds: 30
```

The wrapper sends:

```json
{"input": "eval prompt"}
```

By default it reads the response field named `output`. Use `--input-field` and `--output-field` when your service uses different names.

Optional headers:

```yaml
command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --header Authorization:Bearer-token"
```

Do not put real secrets in committed config files. Use environment-specific wrappers or local config overlays for credentials.

## SDK or Queue Agents

Create a tiny wrapper script that reads `stdin`, calls your SDK or queue, prints the final answer, and exits non-zero on runtime failure. The eval runner does not need to know the internal transport.
