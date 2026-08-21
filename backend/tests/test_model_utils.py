import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.model import PreferenceModel  # noqa: E402
from app.model_utils import (  # noqa: E402
    EvaluationExample,
    EvaluationPredictionError,
    evaluate_preference_model,
    load_evaluation_examples,
)


class _LengthPreferencePredictor:
    """Predicts the longer response, independent of its A/B position."""

    def predict(self, prompt: str, response_a: str, response_b: str) -> SimpleNamespace:
        del prompt
        if len(response_a) >= len(response_b):
            return SimpleNamespace(score_b=0.25, winner="A")
        return SimpleNamespace(score_b=0.75, winner="B")


class _FirstPositionPredictor:
    def predict(self, prompt: str, response_a: str, response_b: str) -> SimpleNamespace:
        del prompt, response_a, response_b
        return SimpleNamespace(score_b=0.25, winner="A")


class _TiePredictor:
    def predict(self, prompt: str, response_a: str, response_b: str) -> SimpleNamespace:
        del prompt, response_a, response_b
        return SimpleNamespace(score_b=0.5, winner="Tie")


class ModelUtilsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.examples = [
            EvaluationExample("p1", "brief", "much longer", 1),
            EvaluationExample("p2", "noticeably longer", "tiny", 0),
        ]

    def test_test_csv_has_expected_contract(self) -> None:
        examples = load_evaluation_examples(ROOT / "preprocess" / "test.csv", limit=2)

        self.assertEqual(len(examples), 2)
        self.assertTrue(all(example.label in {0, 1} for example in examples))
        self.assertTrue(all(example.prompt and example.response_a and example.response_b for example in examples))

    def test_standard_metrics_and_bias_checks(self) -> None:
        with patch("app.model_utils.load_evaluation_examples", return_value=self.examples):
            summary = evaluate_preference_model(_LengthPreferencePredictor(), "unused.csv")

        self.assertEqual(summary.examples_evaluated, 2)
        self.assertEqual(summary.metrics.accuracy, 1.0)
        self.assertEqual(summary.metrics.precision, 1.0)
        self.assertEqual(summary.metrics.recall, 1.0)
        self.assertEqual(summary.metrics.f1, 1.0)
        self.assertEqual(summary.metrics.roc_auc, 1.0)
        self.assertEqual(summary.metrics.confusion_matrix, [[1, 0], [0, 1]])
        self.assertEqual(summary.position_bias.inconsistent_swaps, 0)
        self.assertEqual(summary.position_bias.combined_first_position_win_rate, 0.5)
        self.assertEqual(summary.verbosity_bias.longer_response_win_rate, 1.0)
        self.assertEqual(
            summary.verbosity_bias.longer_response_win_rate_excess_over_chance, 0.5
        )
        self.assertEqual(summary.verbosity_bias.length_delta_prediction_correlation, -1.0)

    def test_position_bias_marks_winners_that_do_not_flip_after_swap(self) -> None:
        with patch("app.model_utils.load_evaluation_examples", return_value=self.examples):
            summary = evaluate_preference_model(_FirstPositionPredictor(), "unused.csv")

        self.assertEqual(summary.position_bias.consistent_swaps, 0)
        self.assertEqual(summary.position_bias.inconsistent_swaps, 2)
        self.assertEqual(summary.position_bias.inconsistent_swap_rate, 1.0)
        self.assertEqual(summary.position_bias.combined_first_position_win_rate, 1.0)

    def test_constant_length_correlation_is_reported_as_unavailable(self) -> None:
        equal_length_examples = [
            EvaluationExample("p1", "same", "size", 0),
            EvaluationExample("p2", "four", "long", 1),
        ]
        with patch(
            "app.model_utils.load_evaluation_examples", return_value=equal_length_examples
        ):
            summary = evaluate_preference_model(_FirstPositionPredictor(), "unused.csv")

        self.assertIsNone(summary.verbosity_bias.longer_response_win_rate)
        self.assertIsNone(summary.verbosity_bias.length_delta_prediction_correlation)
        self.assertIn("length deltas are constant", summary.verbosity_bias.correlation_reason)

    def test_evaluator_rejects_non_binary_prediction(self) -> None:
        with patch("app.model_utils.load_evaluation_examples", return_value=self.examples):
            with self.assertRaises(EvaluationPredictionError):
                evaluate_preference_model(_TiePredictor(), "unused.csv")

    def test_real_preference_inference_contract_uses_ab_and_expected_text(self) -> None:
        import torch

        class Tokenizer:
            def __init__(self) -> None:
                self.calls: list[tuple[str, dict]] = []

            def __call__(self, text: str, **kwargs: object) -> dict[str, object]:
                self.calls.append((text, kwargs))
                return {"input_ids": torch.tensor([[1]])}

        class ScalarRewardModel:
            def __call__(self, **kwargs: object) -> SimpleNamespace:
                del kwargs
                # Equal rewards exercise the A tie-break used by production
                # scalar-reward inference, without loading the 500 MB checkpoint.
                return SimpleNamespace(logits=torch.tensor([0.0]))

        settings = Settings(use_dummy_model=False, max_length=256)
        preference_model = PreferenceModel(settings)
        tokenizer = Tokenizer()
        preference_model.tokenizer = tokenizer
        preference_model.model = ScalarRewardModel()
        preference_model.demo_mode = False

        result = preference_model.predict("Prompt", "Answer A", "Answer B")

        self.assertEqual(result.winner, "A")
        self.assertIn(result.winner, {"A", "B"})
        self.assertEqual(result.score_a, 0.5)
        self.assertEqual(result.score_b, 0.5)
        self.assertEqual(
            [text for text, _ in tokenizer.calls],
            ["Prompt\nResponse: Answer A", "Prompt\nResponse: Answer B"],
        )
        self.assertTrue(all(call["truncation"] for _, call in tokenizer.calls))
        self.assertTrue(all(call["max_length"] == 256 for _, call in tokenizer.calls))


if __name__ == "__main__":
    unittest.main()
