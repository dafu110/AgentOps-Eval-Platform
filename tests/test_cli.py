import unittest
from pathlib import Path
import tempfile

from agentops_eval.cli import _select_agents
from agentops_eval.cli import _resolve_run_id
from agentops_eval.models import AgentConfig


class CliTests(unittest.TestCase):
    def test_select_agents_returns_all_when_no_selection(self):
        agents = [
            AgentConfig(name="one", command="python one.py"),
            AgentConfig(name="two", command="python two.py"),
        ]

        self.assertEqual(_select_agents(agents, None), agents)

    def test_select_agents_filters_in_requested_order(self):
        agents = [
            AgentConfig(name="one", command="python one.py"),
            AgentConfig(name="two", command="python two.py"),
        ]

        selected = _select_agents(agents, ["two", "one"])

        self.assertEqual([agent.name for agent in selected], ["two", "one"])

    def test_select_agents_rejects_unknown_agent(self):
        agents = [AgentConfig(name="one", command="python one.py")]

        with self.assertRaisesRegex(SystemExit, "Unknown agent"):
            _select_agents(agents, ["missing"])

    def test_resolve_run_id_reads_latest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            (runs_dir / "latest.txt").write_text("run-123", encoding="utf-8")

            self.assertEqual(_resolve_run_id(runs_dir, "latest"), "run-123")
