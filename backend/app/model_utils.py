"""Evaluation helpers for the trained pairwise preference model.

The held-out dataset stores binary labels where 0 means Response A is preferred
and 1 means Response B is preferred.  This module deliberately calls the same
``predict`` method used by the API so every evaluation uses the model's
``{prompt}\nResponse: {response}`` input format and configured token limit.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)


REQUIRED_TEST_COLUMNS = frozenset({"prompt", "response_a", "response_b", "label"})


class EvaluationDataError(ValueError):
    """Raised when a held-out evaluation CSV does not match the expected contract."""


class EvaluationPredictionError(RuntimeError):
    """Raised when a predictor does not honour the A/B preference contract."""


class PredictionResult(Protocol):
    """The subset of ``Prediction`` required for evaluation."""

    score_b: float
    winner: str


class PreferencePredictor(Protocol):
    """A model capable of comparing two responses for one prompt."""

    def predict(
        self, prompt: str, response_a: str, response_b: str
    ) -> PredictionResult: ...


@dataclass(frozen=True)
class EvaluationExample:
    prompt: str
    response_a: str
    response_b: str
    label: int


@dataclass(frozen=True)
class StandardMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    roc_auc_reason: str | None
    confusion_matrix: list[list[int]]
    class_metrics: dict[str, dict[str, float | int]]


@dataclass(frozen=True)
class PositionBiasMetrics:
    pairs_evaluated: int
    consistent_swaps: int
    inconsistent_swaps: int
    consistent_swap_rate: float
    inconsistent_swap_rate: float
    original_first_position_win_rate: float
    swapped_first_position_win_rate: float
    combined_first_position_win_rate: float


@dataclass(frozen=True)
class VerbosityBiasMetrics:
    pairs_evaluated: int
    pairs_with_different_lengths: int
    longer_response_wins: int
    longer_response_win_rate: float | None
    longer_response_win_rate_excess_over_chance: float | None
    length_delta_prediction_correlation: float | None
    correlation_reason: str | None


@dataclass(frozen=True)
class EvaluationSummary:
    examples_evaluated: int
    metrics: StandardMetrics
    position_bias: PositionBiasMetrics
    verbosity_bias: VerbosityBiasMetrics


def load_evaluation_examples(
    test_csv: str | Path, *, limit: int | None = None
) -> list[EvaluationExample]:
    """Read and validate held-out examples without changing the source CSV."""

    if limit is not None and limit < 1:
        raise ValueError("Evaluation limit must be at least 1 when provided.")

    path = Path(test_csv)
    if not path.is_file():
        raise EvaluationDataError(f"Evaluation test file does not exist: {path}")

    examples: list[EvaluationExample] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_TEST_COLUMNS - fields
        if missing:
            names = ", ".join(sorted(missing))
            raise EvaluationDataError(f"Evaluation CSV is missing required columns: {names}")

        for row_number, row in enumerate(reader, start=2):
            try:
                prompt = row["prompt"]
                response_a = row["response_a"]
                response_b = row["response_b"]
                raw_label = row["label"]
            except KeyError as exc:  # Defensive: DictReader field names were checked above.
                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} is missing {exc.args[0]!r}."
                ) from exc

            if not all(isinstance(value, str) and value.strip() for value in (prompt, response_a, response_b)):
                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} has an empty prompt or response."
                )
            try:
                label = int(raw_label)
            except (TypeError, ValueError) as exc:
                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} has a non-binary label: {raw_label!r}."
                ) from exc
            if label not in {0, 1}:
                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} has label {label}; expected 0 (A) or 1 (B)."
                )

            examples.append(
                EvaluationExample(
                    prompt=prompt,
                    response_a=response_a,
                    response_b=response_b,
                    label=label,
                )
            )
            if limit is not None and len(examples) >= limit:
                break

    if not examples:
        raise EvaluationDataError("Evaluation CSV contains no examples.")
    return examples


def evaluate_preference_model(
    predictor: PreferencePredictor,
    test_csv: str | Path,
    *,
    limit: int | None = None,
) -> EvaluationSummary:
    """Evaluate a preference predictor and calculate order and length signals.

    Standard metrics are calculated from the original A/B ordering only.  For
    position analysis each pair is submitted again with the responses swapped.
    A swap is consistent only when the winner flips positions: original A must
    become swapped B, and original B must become swapped A.
    """

    examples = load_evaluation_examples(test_csv, limit=limit)
    actual_labels: list[int] = []
    predicted_labels: list[int] = []
    probability_b: list[float] = []
    original_winners: list[str] = []
    swapped_winners: list[str] = []
    length_deltas: list[int] = []

    for example_number, example in enumerate(examples, start=1):
        original = predictor.predict(
            example.prompt, example.response_a, example.response_b
        )
        original_winner = _validate_winner(original.winner, example_number, "original")
        probability_b.append(
            _validate_probability_b(original.score_b, example_number)
        )

        swapped = predictor.predict(
            example.prompt, example.response_b, example.response_a
        )
        swapped_winner = _validate_winner(swapped.winner, example_number, "swapped")

        actual_labels.append(example.label)
        predicted_labels.append(_winner_to_label(original_winner))
        original_winners.append(original_winner)
        swapped_winners.append(swapped_winner)
        length_deltas.append(len(example.response_a) - len(example.response_b))

    return EvaluationSummary(
        examples_evaluated=len(examples),
        metrics=_calculate_standard_metrics(
            actual_labels=actual_labels,
            predicted_labels=predicted_labels,
            probability_b=probability_b,
        ),
        position_bias=_calculate_position_bias(original_winners, swapped_winners),
        verbosity_bias=_calculate_verbosity_bias(length_deltas, original_winners),
    )


def _calculate_standard_metrics(
    *,
    actual_labels: Sequence[int],
    predicted_labels: Sequence[int],
    probability_b: Sequence[float],
) -> StandardMetrics:
    precision_values, recall_values, f1_values, support_values = (
        precision_recall_fscore_support(
            actual_labels,
            predicted_labels,
            labels=[0, 1],
            zero_division=0,
        )
    )
    class_metrics = {
        "A": {
            "precision": float(precision_values[0]),
            "recall": float(recall_values[0]),
            "f1": float(f1_values[0]),
            "support": int(support_values[0]),
        },
        "B": {
            "precision": float(precision_values[1]),
            "recall": float(recall_values[1]),
            "f1": float(f1_values[1]),
            "support": int(support_values[1]),
        },
    }

    roc_auc: float | None = None
    roc_auc_reason: str | None = None
    if len(set(actual_labels)) < 2:
        roc_auc_reason = "ROC-AUC requires both A-preferred and B-preferred labels."
    else:
        try:
            roc_auc = float(roc_auc_score(actual_labels, probability_b))
        except ValueError as exc:
            roc_auc_reason = f"ROC-AUC could not be calculated: {exc}"

    return StandardMetrics(
        accuracy=float(accuracy_score(actual_labels, predicted_labels)),
        # Macro averaging weights A and B equally rather than treating an
        # arbitrary response position as the positive class.
        precision=float(
            precision_score(actual_labels, predicted_labels, average="macro", zero_division=0)
        ),
        recall=float(
            recall_score(actual_labels, predicted_labels, average="macro", zero_division=0)
        ),
        f1=float(f1_score(actual_labels, predicted_labels, average="macro", zero_division=0)),
        roc_auc=roc_auc,
        roc_auc_reason=roc_auc_reason,
        confusion_matrix=confusion_matrix(
            actual_labels, predicted_labels, labels=[0, 1]
        ).tolist(),
        class_metrics=class_metrics,
    )


def _calculate_position_bias(
    original_winners: Sequence[str], swapped_winners: Sequence[str]
) -> PositionBiasMetrics:
    total = len(original_winners)
    consistent = sum(
        swapped == _opposite_winner(original)
        for original, swapped in zip(original_winners, swapped_winners, strict=True)
    )
    original_first_wins = sum(winner == "A" for winner in original_winners)
    swapped_first_wins = sum(winner == "A" for winner in swapped_winners)

    return PositionBiasMetrics(
        pairs_evaluated=total,
        consistent_swaps=consistent,
        inconsistent_swaps=total - consistent,
        consistent_swap_rate=consistent / total,
        inconsistent_swap_rate=(total - consistent) / total,
        original_first_position_win_rate=original_first_wins / total,
        swapped_first_position_win_rate=swapped_first_wins / total,
        # With no position effect, each pair contributes exactly one winner in
        # the first slot across original and swapped runs, yielding 0.5.
        combined_first_position_win_rate=(original_first_wins + swapped_first_wins)
        / (2 * total),
    )


def _calculate_verbosity_bias(
    length_deltas: Sequence[int], original_winners: Sequence[str]
) -> VerbosityBiasMetrics:
    longer_response_wins = 0
    pairs_with_different_lengths = 0
    predicted_labels = [_winner_to_label(winner) for winner in original_winners]

    for delta, winner in zip(length_deltas, original_winners, strict=True):
        if delta == 0:
            continue
        pairs_with_different_lengths += 1
        longer_won = (delta > 0 and winner == "A") or (delta < 0 and winner == "B")
        longer_response_wins += int(longer_won)

    correlation, correlation_reason = _safe_pearson_correlation(
        length_deltas, predicted_labels
    )
    longer_response_win_rate: float | None = None
    excess_over_chance: float | None = None
    if pairs_with_different_lengths:
        longer_response_win_rate = longer_response_wins / pairs_with_different_lengths
        excess_over_chance = longer_response_win_rate - 0.5

    return VerbosityBiasMetrics(
        pairs_evaluated=len(length_deltas),
        pairs_with_different_lengths=pairs_with_different_lengths,
        longer_response_wins=longer_response_wins,
        longer_response_win_rate=longer_response_win_rate,
        longer_response_win_rate_excess_over_chance=excess_over_chance,
        length_delta_prediction_correlation=correlation,
        correlation_reason=correlation_reason,
    )


def _safe_pearson_correlation(
    x_values: Sequence[int], y_values: Sequence[int]
) -> tuple[float | None, str | None]:
    """Return Pearson correlation or a clear reason why it is undefined."""

    if len(x_values) < 2:
        return None, "Correlation requires at least two evaluation pairs."
    if len(set(x_values)) < 2:
        return None, "Correlation is undefined because response-length deltas are constant."
    if len(set(y_values)) < 2:
        return None, "Correlation is undefined because model predictions are constant."

    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)
    )
    x_sum_squares = sum((x - x_mean) ** 2 for x in x_values)
    y_sum_squares = sum((y - y_mean) ** 2 for y in y_values)
    denominator = math.sqrt(x_sum_squares * y_sum_squares)
    if denominator == 0:  # Defensive against numerical edge cases.
        return None, "Correlation is undefined because an input has no variance."
    return float(numerator / denominator), None


def _validate_winner(winner: str, example_number: int, ordering: str) -> str:
    if winner not in {"A", "B"}:
        raise EvaluationPredictionError(
            f"{ordering.capitalize()} prediction for example {example_number} returned "
            f"{winner!r}; expected only 'A' or 'B'."
        )
    return winner


def _validate_probability_b(score_b: float, example_number: int) -> float:
    try:
        probability_b = float(score_b)
    except (TypeError, ValueError) as exc:
        raise EvaluationPredictionError(
            f"Prediction for example {example_number} has an invalid score_b value."
        ) from exc
    if not math.isfinite(probability_b) or not 0.0 <= probability_b <= 1.0:
        raise EvaluationPredictionError(
            f"Prediction for example {example_number} has score_b outside [0, 1]."
        )
    return probability_b


def _winner_to_label(winner: str) -> int:
    return 0 if winner == "A" else 1


def _opposite_winner(winner: str) -> str:
    return "B" if winner == "A" else "A"
