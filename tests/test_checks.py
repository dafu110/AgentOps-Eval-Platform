import unittest

from agentops_eval.checks import validate_output
from agentops_eval.models import EvalCase, EvalChecks


class CheckTests(unittest.TestCase):
    def test_validate_output_accepts_required_substrings(self):
        case = EvalCase(
            case_id="case-1",
            input_text="input",
            checks=EvalChecks(contains=("hello",), not_contains=("secret",), min_length=5),
        )

        checks = validate_output(case, "hello world")

        self.assertTrue(all(check.passed for check in checks))

    def test_validate_output_checks_json_fields(self):
        case = EvalCase(
            case_id="case-2",
            input_text="input",
            checks=EvalChecks(expect_json=True, json_fields=("status",)),
        )

        checks = validate_output(case, '{"status":"ok"}')

        self.assertTrue(all(check.passed for check in checks))


if __name__ == "__main__":
    unittest.main()
