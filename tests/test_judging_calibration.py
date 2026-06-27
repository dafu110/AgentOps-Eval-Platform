import json
import tempfile
import unittest
from pathlib import Path

from agentops_eval.calibration import calibrate_judge
from agentops_eval.judging import judge_output
from agentops_eval.models import EvalCase, EvalChecks


class JudgingCalibrationTests(unittest.TestCase):
    def test_heuristic_judge_scores_rubric_case(self):
        case = EvalCase(
            case_id="case-1",
            input_text="input",
            checks=EvalChecks(contains=("AgentOps",), rubric="Mentions AgentOps", min_score=0.8),
        )

        result = judge_output(case, "AgentOps is ready")

        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.score, 0.8)

    def test_calibrate_judge_compares_human_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results_path = root / "results.jsonl"
            labels_path = root / "labels.jsonl"
            results_path.write_text(
                json.dumps({"agent": "a", "case_id": "c", "score": 0.9}) + "\n",
                encoding="utf-8",
            )
            labels_path.write_text(
                json.dumps({"agent": "a", "case_id": "c", "human_score": 0.85}) + "\n",
                encoding="utf-8",
            )

            report = calibrate_judge(results_path, labels_path, tolerance=0.1)

            self.assertEqual(report["compared"], 1)
            self.assertEqual(report["agreement_rate"], 1.0)
