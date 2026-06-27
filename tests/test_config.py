from pathlib import Path
import tempfile
import unittest

from agentops_eval.config import ConfigError, load_agent_registry


class ConfigTests(unittest.TestCase):
    def test_load_agent_registry_reads_any_number_of_agents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "agents.yaml"
            config.write_text(
                "\n".join(
                    [
                        "agents:",
                        "  one:",
                        '    command: "python one.py"',
                        "    timeout_seconds: 5",
                        "  two:",
                        '    command: "python two.py"',
                        "    timeout_seconds: 6",
                        "  four:",
                        '    command: "python four.py"',
                        "    timeout_seconds: 7",
                        "  five:",
                        '    command: "python five.py"',
                        "    timeout_seconds: 8",
                    ]
                ),
                encoding="utf-8",
            )

            agents = load_agent_registry(config)

            self.assertEqual([agent.name for agent in agents], ["one", "two", "four", "five"])
            self.assertEqual(agents[1].timeout_seconds, 6)

    def test_load_agent_registry_reads_extended_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "agents.yaml"
            config.write_text(
                "\n".join(
                    [
                        "agents:",
                        "  peopleops:",
                        '    adapter: "http-json"',
                        '    command: "python -m agentops_eval.http_agent --url http://localhost"',
                        '    repo_url: "https://github.com/example/repo"',
                        '    health_url: "http://localhost/health"',
                        "    timeout_seconds: 12",
                        "    requires_approval: true",
                        "    danger_level: high",
                        "    env_allowlist: OPENAI_API_KEY,MODEL",
                    ]
                ),
                encoding="utf-8",
            )

            agent = load_agent_registry(config)[0]

            self.assertEqual(agent.adapter, "http-json")
            self.assertTrue(agent.requires_approval)
            self.assertEqual(agent.env_allowlist, ("OPENAI_API_KEY", "MODEL"))

    def test_load_agent_registry_requires_at_least_one_agent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "agents.yaml"
            config.write_text("agents:\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "at least 1 agent"):
                load_agent_registry(config)

    def test_load_agent_registry_rejects_duplicate_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir) / "agents.yaml"
            config.write_text(
                "\n".join(
                    [
                        "agents:",
                        "  one:",
                        '    command: "python one.py"',
                        "  one:",
                        '    command: "python one-again.py"',
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "Duplicate agent names"):
                load_agent_registry(config)


if __name__ == "__main__":
    unittest.main()
