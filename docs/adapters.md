# Real Agent Adapters

AgentOps-Eval-Platform invokes real agents through small command adapters. This keeps the runner stable while each agent can be implemented as a CLI, HTTP service, SDK wrapper, or queue worker.

The registry `adapter` value is not just a label: the runner validates and dispatches through it. Unsupported adapter names fail the run/config load instead of silently falling back to command execution.

Supported adapters:

| Adapter | Purpose | Execution shape |
|---|---|---|
| `command` | Plain stdin/stdout CLI or SDK wrapper | Runs the configured Python command. |
| `http-json` | Generic HTTP JSON agent | Runs `agentops_eval.http_agent`. |
| `agentflow-http` | AgentFlow Studio integration | Runs `agentops_eval.agentflow_adapter`. |
| `bigdata-http` | Big Data Analytics Agent integration | Runs `agentops_eval.bigdata_adapter`. |

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
    adapter: command
    command: "python path/to/planner_agent.py"
    timeout_seconds: 30
```

## Built-In HTTP Adapter

For HTTP agents, use the bundled wrapper:

```yaml
agents:
  support_agent:
    adapter: http-json
    command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --output-field answer"
    timeout_seconds: 30
```

The wrapper sends:

```json
{"input": "eval prompt"}
```

By default it reads the response field named `output`. Use `--input-field` and `--output-field` when your service uses different names. Nested output paths such as `data.answer` are supported.

Optional headers:

```yaml
command: "python -m agentops_eval.http_agent --url http://localhost:8080/invoke --header Authorization:Bearer-token"
```

Do not put real secrets in committed config files. Use environment-specific wrappers or local config overlays for credentials.

## Existing Agent Registry

The default `configs/agents.yaml` is wired for the three existing repositories:

| Agent | Repository | Adapter | Endpoint |
|---|---|---|---|
| `peopleops` | `dafu110/peopleops-agent-platform` | `http_agent` | `POST /chat` |
| `agentflow` | `dafu110/Agent-Flow-Studio` | `agentflow_adapter` | `POST /api/generate-canvas` |
| `bigdata` | `dafu110/Big-Data-Analytics-Agent` | `bigdata_adapter` | `POST /api/analyze` |

Expected local service ports:

```powershell
# peopleops-agent-platform
python -m uvicorn api:app --host 127.0.0.1 --port 8001

# Agent-Flow-Studio/canvas-backend
python -m uvicorn main:app --host 127.0.0.1 --port 8002

# Big-Data-Analytics-Agent
python app.py
```

Then run:

```powershell
agentops-eval run --suite sample --config configs/agents.yaml
```

Use `configs/agents.mock.yaml` when those services are not running.

This is intentional: real-agent mode should fail loudly when an agent service is unavailable.

## SDK or Queue Agents

Create a tiny wrapper script that reads `stdin`, calls your SDK or queue, prints the final answer, and exits non-zero on runtime failure. The eval runner does not need to know the internal transport.

## Security Contract

- Registry commands are restricted to Python entrypoints.
- Dangerous shell tokens and agents marked `requires_approval` require `--approve-dangerous`.
- Only `PATH`, `PYTHONPATH`, `PYTHONIOENCODING`, and explicitly allowlisted env vars are passed to child processes.
- stdout/stderr are redacted for common secret shapes before persistence.
