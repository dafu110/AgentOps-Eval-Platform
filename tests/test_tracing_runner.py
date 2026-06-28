import json
import tempfile
import unittest
from pathlib import Path

from agentops_eval.models import AgentConfig, EvalCase, EvalChecks
from agentops_eval.runner import run_suite
from agentops_eval.tracing import resolve_trace_path


class TracingRunnerTests(unittest.TestCase):
    def test_run_suite_writes_trace_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            agents = [AgentConfig(name="alpha", command="python -m agentops_eval.mock_agent --name alpha")]
            cases = [
                EvalCase(
                    case_id="hello",
                    input_text="Say hello and mention AgentOps.",
                    checks=EvalChecks(contains=("hello", "AgentOps"), min_length=5),
                )
            ]

            run_dir = run_suite(agents, cases, runs_dir, "trace-test")
            result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            trace_path = resolve_trace_path(runs_dir, "trace-test", result["trace_id"])
            trace = json.loads(trace_path.read_text(encoding="utf-8"))

            self.assertEqual(trace["trace_id"], result["trace_id"])
            self.assertEqual(trace["agent"]["name"], "alpha")
            self.assertEqual(trace["case"]["id"], "hello")

    def test_run_suite_records_rubric_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            agents = [AgentConfig(name="alpha", command="python -m agentops_eval.mock_agent --name alpha")]
            cases = [
                EvalCase(
                    case_id="hello",
                    input_text="Say hello and mention AgentOps.",
                    checks=EvalChecks(
                        contains=("hello", "AgentOps"),
                        min_length=5,
                        rubric="Response mentions AgentOps.",
                        min_score=0.8,
                    ),
                )
            ]

            run_dir = run_suite(agents, cases, runs_dir, "rubric-test")
            result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))

            self.assertTrue(result["passed"])
            self.assertGreaterEqual(result["score"], 0.8)
            self.assertGreaterEqual(summary["avg_score"], 0.8)
            self.assertEqual(summary["judge_modes"], ["heuristic"])

    def test_run_suite_fails_unsupported_adapter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            agents = [AgentConfig(name="alpha", command="python -m agentops_eval.mock_agent --name alpha", adapter="unknown")]
            cases = [
                EvalCase(
                    case_id="hello",
                    input_text="Say hello and mention AgentOps.",
                    checks=EvalChecks(contains=("hello", "AgentOps"), min_length=5),
                )
            ]

            run_dir = run_suite(agents, cases, runs_dir, "adapter-test")
            result = json.loads((run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()[0])

            self.assertFalse(result["passed"])
            self.assertEqual(result["error_type"], "unsupported_adapter")


if __name__ == "__main__":
    unittest.main()
