import unittest

from agentops_eval.cli import _select_agents
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
