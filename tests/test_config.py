from pathlib import Path
import tempfile
import unittest

from agentops_eval.config import load_agent_registry


class ConfigTests(unittest.TestCase):
    def test_load_agent_registry_reads_three_agents(self):
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
                        "  three:",
                        '    command: "python three.py"',
                        "    timeout_seconds: 7",
                    ]
                ),
                encoding="utf-8",
            )

            agents = load_agent_registry(config)

            self.assertEqual([agent.name for agent in agents], ["one", "two", "three"])
            self.assertEqual(agents[1].timeout_seconds, 6)


if __name__ == "__main__":
    unittest.main()
