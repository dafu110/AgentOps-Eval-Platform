import unittest

from agentops_eval.models import AgentConfig
from agentops_eval.security import SecurityPolicyError, redact_secrets, validate_command_policy


class SecurityTests(unittest.TestCase):
    def test_redact_secrets_masks_common_secret_shapes(self):
        text = "api_key=abc123 token:xyz sk-1234567890abcdef"

        redacted = redact_secrets(text)

        self.assertNotIn("abc123", redacted)
        self.assertNotIn("xyz", redacted)
        self.assertNotIn("sk-1234567890abcdef", redacted)

    def test_validate_command_policy_blocks_non_python_executable(self):
        agent = AgentConfig(name="bad", command="curl http://example.com")

        with self.assertRaises(SecurityPolicyError):
            validate_command_policy(agent)

    def test_validate_command_policy_allows_python_adapter(self):
        agent = AgentConfig(name="ok", command="python -m agentops_eval.mock_agent --name ok")

        self.assertEqual(validate_command_policy(agent)[0], "python")
