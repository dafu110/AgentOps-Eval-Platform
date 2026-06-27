import tempfile
import unittest
from pathlib import Path

from agentops_eval.models import AgentConfig, EvalCase, EvalChecks
from agentops_eval.monitor import run_monitor


class MonitorTests(unittest.TestCase):
    def test_run_monitor_returns_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshots = run_monitor(
                agents=[AgentConfig(name="alpha", command="python -m agentops_eval.mock_agent --name alpha")],
                cases=[
                    EvalCase(
                        case_id="hello",
                        input_text="Say hello and mention AgentOps.",
                        checks=EvalChecks(contains=("hello", "AgentOps"), min_length=5),
                    )
                ],
                runs_dir=Path(temp_dir),
                interval_seconds=1,
                iterations=1,
                min_pass_rate=0.9,
            )

            self.assertEqual(len(snapshots), 1)
            self.assertFalse(snapshots[0]["alert"])
            self.assertTrue((Path(temp_dir) / "monitor" / "history.jsonl").exists())
            self.assertTrue((Path(temp_dir) / "monitor" / "dashboard.html").exists())


if __name__ == "__main__":
    unittest.main()
