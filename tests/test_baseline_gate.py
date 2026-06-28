import json
import tempfile
import unittest
from pathlib import Path

from agentops_eval.baseline import compare_to_baseline, promote_baseline
from agentops_eval.gate import evaluate_gate


class BaselineGateTests(unittest.TestCase):
    def test_compare_to_baseline_reports_pass_rate_delta(self):
        current = {"pass_rate": 0.9, "by_agent": {"a": {"pass_rate": 0.9, "p95_latency_ms": 100}}}
        baseline = {"pass_rate": 1.0, "by_agent": {"a": {"pass_rate": 1.0, "p95_latency_ms": 90}}}

        comparison = compare_to_baseline(current, baseline)

        self.assertEqual(comparison["pass_rate_delta"], -0.1)
        self.assertEqual(comparison["by_agent"]["a"]["current_p95_latency_ms"], 100)

    def test_promote_baseline_and_gate_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            run_dir = runs_dir / "run-1"
            run_dir.mkdir()
            summary = {
                "total": 2,
                "passed": 2,
                "failed": 0,
                "pass_rate": 1.0,
                "by_agent": {"a": {"pass_rate": 1.0, "p95_latency_ms": 10}},
            }
            (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

            promote_baseline(runs_dir, "run-1", "main")
            passed, report = evaluate_gate(runs_dir, "run-1", "main", 0.9, 0.02, 0.1)

            self.assertTrue(passed)
            self.assertTrue((run_dir / "gate.json").exists())
            self.assertTrue(all(check["passed"] for check in report["checks"]))

    def test_gate_fails_low_pass_rate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            run_dir = runs_dir / "run-1"
            run_dir.mkdir()
            summary = {"total": 2, "passed": 1, "failed": 1, "pass_rate": 0.5, "by_agent": {}}
            (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

            passed, report = evaluate_gate(runs_dir, "run-1", None, 0.9, 0.02, 0.1)

            self.assertFalse(passed)
            self.assertFalse(report["checks"][0]["passed"])

    def test_gate_can_require_external_judge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            run_dir = runs_dir / "run-1"
            run_dir.mkdir()
            summary = {
                "total": 1,
                "passed": 1,
                "failed": 0,
                "pass_rate": 1.0,
                "avg_score": 0.95,
                "judge_modes": ["heuristic"],
                "by_agent": {},
            }
            (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

            passed, report = evaluate_gate(runs_dir, "run-1", None, 0.9, 0.02, 0.1, 0.8, True)

            self.assertFalse(passed)
            self.assertFalse(report["checks"][-1]["passed"])


if __name__ == "__main__":
    unittest.main()
