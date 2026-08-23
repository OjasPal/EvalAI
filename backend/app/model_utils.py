"""Evaluation helpers for the EvalAI pairwise preference model.

The held-out dataset stores binary labels:
0 = Response A preferred
1 = Response B preferred

This module preserves the existing evaluation contract while adding
bias-aware analysis helpers for position and verbosity effects.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence, cast

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)


REQUIRED_TEST_COLUMNS = frozenset(
    {
        "prompt",
        "response_a",
        "response_b",
        "label",
    }
)


class EvaluationDataError(ValueError):
    """Raised when an evaluation CSV is invalid."""


class EvaluationPredictionError(RuntimeError):
    """Raised when a predictor violates the A/B contract."""


class PredictionResult(Protocol):
    score_a: float
    score_b: float
    winner: str


class PreferencePredictor(Protocol):
    def predict(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
    ) -> PredictionResult:
        ...


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

    # New bias-aware indicators.
    order_neutrality_score: float
    bias_severity: str


@dataclass(frozen=True)
class VerbosityBiasMetrics:
    pairs_evaluated: int
    pairs_with_different_lengths: int
    longer_response_wins: int
    longer_response_win_rate: float | None
    longer_response_win_rate_excess_over_chance: float | None
    length_delta_prediction_correlation: float | None
    correlation_reason: str | None

    # New bias-aware indicators.
    verbosity_bias_magnitude: float | None
    bias_severity: str


@dataclass(frozen=True)
class BiasMitigationResult:
    """Order-aware interpretation of a pairwise prediction.

    This does not change the live /predict contract. It provides a
    conservative interpretation of predictions when the same pair is
    evaluated in both response orders.
    """

    original_winner: str
    swapped_winner: str
    response_consistent: bool
    debiased_winner: str
    confidence_penalty: float
    order_bias_detected: bool


@dataclass(frozen=True)
class EvaluationSummary:
    examples_evaluated: int
    metrics: StandardMetrics
    position_bias: PositionBiasMetrics
    verbosity_bias: VerbosityBiasMetrics


def load_evaluation_examples(
    test_csv: str | Path,
    *,
    limit: int | None = None,
) -> list[EvaluationExample]:
    """Read and validate held-out examples."""

    if limit is not None and limit < 1:
        raise ValueError(
            "Evaluation limit must be at least 1 when provided."
        )

    path = Path(test_csv)

    if not path.is_file():
        raise EvaluationDataError(
            f"Evaluation test file does not exist: {path}"
        )

    examples: list[EvaluationExample] = []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        reader = csv.DictReader(handle)

        fields = set(reader.fieldnames or [])

        missing = REQUIRED_TEST_COLUMNS - fields

        if missing:
            names = ", ".join(sorted(missing))

            raise EvaluationDataError(
                "Evaluation CSV is missing required columns: "
                f"{names}"
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):

            try:
                prompt = row["prompt"]
                response_a = row["response_a"]
                response_b = row["response_b"]
                raw_label = row["label"]

            except KeyError as exc:

                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} "
                    f"is missing {exc.args[0]!r}."
                ) from exc

            if not all(
                isinstance(value, str)
                and value.strip()
                for value in (
                    prompt,
                    response_a,
                    response_b,
                )
            ):
                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} "
                    "has an empty prompt or response."
                )

            try:
                label = int(raw_label)

            except (TypeError, ValueError) as exc:

                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} "
                    f"has a non-binary label: {raw_label!r}."
                ) from exc

            if label not in {0, 1}:

                raise EvaluationDataError(
                    f"Evaluation CSV row {row_number} "
                    f"has label {label}; expected 0 (A) or 1 (B)."
                )

            examples.append(
                EvaluationExample(
                    prompt=prompt,
                    response_a=response_a,
                    response_b=response_b,
                    label=label,
                )
            )

            if (
                limit is not None
                and len(examples) >= limit
            ):
                break

    if not examples:
        raise EvaluationDataError(
            "Evaluation CSV contains no examples."
        )

    return examples


def evaluate_preference_model(
    predictor: PreferencePredictor,
    test_csv: str | Path,
    *,
    limit: int | None = None,
) -> EvaluationSummary:
    """Evaluate quality plus position and verbosity bias."""

    examples = load_evaluation_examples(
        test_csv,
        limit=limit,
    )

    actual_labels: list[int] = []
    predicted_labels: list[int] = []
    probability_b: list[float] = []

    original_winners: list[str] = []
    swapped_winners: list[str] = []

    length_deltas: list[int] = []

    for example_number, example in enumerate(
        examples,
        start=1,
    ):

        original = predictor.predict(
            example.prompt,
            example.response_a,
            example.response_b,
        )

        original_winner = _validate_winner(
            original.winner,
            example_number,
            "original",
        )

        probability_b.append(
            _validate_probability_b(
                original.score_b,
                example_number,
            )
        )

        swapped = predictor.predict(
            example.prompt,
            example.response_b,
            example.response_a,
        )

        swapped_winner = _validate_winner(
            swapped.winner,
            example_number,
            "swapped",
        )

        actual_labels.append(example.label)

        predicted_labels.append(
            _winner_to_label(original_winner)
        )

        original_winners.append(
            original_winner
        )

        swapped_winners.append(
            swapped_winner
        )

        length_deltas.append(
            len(example.response_a)
            - len(example.response_b)
        )

    return EvaluationSummary(
        examples_evaluated=len(examples),

        metrics=_calculate_standard_metrics(
            actual_labels=actual_labels,
            predicted_labels=predicted_labels,
            probability_b=probability_b,
        ),

        position_bias=_calculate_position_bias(
            original_winners,
            swapped_winners,
        ),

        verbosity_bias=_calculate_verbosity_bias(
            length_deltas,
            original_winners,
        ),
    )


def _calculate_standard_metrics(
    *,
    actual_labels: Sequence[int],
    predicted_labels: Sequence[int],
    probability_b: Sequence[float],
) -> StandardMetrics:

    metric_values = cast(
        tuple[
            Sequence[float],
            Sequence[float],
            Sequence[float],
            Sequence[int],
        ],
        precision_recall_fscore_support(
            actual_labels,
            predicted_labels,
            labels=[0, 1],
            average=None,
            zero_division=0,
        ),
    )
    precision_values, recall_values, f1_values, support_values = metric_values

    class_metrics = {
        "A": {
            "precision": float(
                precision_values[0]
            ),
            "recall": float(
                recall_values[0]
            ),
            "f1": float(
                f1_values[0]
            ),
            "support": int(
                support_values[0]
            ),
        },
        "B": {
            "precision": float(
                precision_values[1]
            ),
            "recall": float(
                recall_values[1]
            ),
            "f1": float(
                f1_values[1]
            ),
            "support": int(
                support_values[1]
            ),
        },
    }

    roc_auc: float | None = None
    roc_auc_reason: str | None = None

    if len(set(actual_labels)) < 2:

        roc_auc_reason = (
            "ROC-AUC requires both "
            "A-preferred and B-preferred labels."
        )

    else:

        try:
            roc_auc = float(
                roc_auc_score(
                    actual_labels,
                    probability_b,
                )
            )

        except ValueError as exc:

            roc_auc_reason = (
                f"ROC-AUC could not be calculated: {exc}"
            )

    return StandardMetrics(
        accuracy=float(
            accuracy_score(
                actual_labels,
                predicted_labels,
            )
        ),

        precision=float(
            precision_score(
                actual_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            )
        ),

        recall=float(
            recall_score(
                actual_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            )
        ),

        f1=float(
            f1_score(
                actual_labels,
                predicted_labels,
                average="macro",
                zero_division=0,
            )
        ),

        roc_auc=roc_auc,

        roc_auc_reason=roc_auc_reason,

        confusion_matrix=confusion_matrix(
            actual_labels,
            predicted_labels,
            labels=[0, 1],
        ).tolist(),

        class_metrics=class_metrics,
    )


def _calculate_position_bias(
    original_winners: Sequence[str],
    swapped_winners: Sequence[str],
) -> PositionBiasMetrics:

    total = len(original_winners)

    if total == 0:
        raise EvaluationDataError(
            "Cannot calculate position bias "
            "without evaluation pairs."
        )

    consistent = sum(
        swapped == _opposite_winner(original)
        for original, swapped in zip(
            original_winners,
            swapped_winners,
            strict=True,
        )
    )

    inconsistent = total - consistent

    original_first_wins = sum(
        winner == "A"
        for winner in original_winners
    )

    swapped_first_wins = sum(
        winner == "A"
        for winner in swapped_winners
    )

    consistent_rate = (
        consistent / total
    )

    inconsistent_rate = (
        inconsistent / total
    )

    combined_first_rate = (
        original_first_wins
        + swapped_first_wins
    ) / (2 * total)

    # 100% = perfectly order-neutral.
    # 0% = every pair behaves inconsistently.
    order_neutrality_score = consistent_rate

    bias_severity = _position_bias_severity(
        inconsistent_rate
    )

    return PositionBiasMetrics(
        pairs_evaluated=total,
        consistent_swaps=consistent,
        inconsistent_swaps=inconsistent,
        consistent_swap_rate=consistent_rate,
        inconsistent_swap_rate=inconsistent_rate,
        original_first_position_win_rate=(
            original_first_wins / total
        ),
        swapped_first_position_win_rate=(
            swapped_first_wins / total
        ),
        combined_first_position_win_rate=(
            combined_first_rate
        ),
        order_neutrality_score=(
            order_neutrality_score
        ),
        bias_severity=bias_severity,
    )


def _position_bias_severity(
    inconsistent_rate: float,
) -> str:

    if inconsistent_rate <= 0.10:
        return "Low"

    if inconsistent_rate <= 0.25:
        return "Moderate"

    return "High"


def _calculate_verbosity_bias(
    length_deltas: Sequence[int],
    original_winners: Sequence[str],
) -> VerbosityBiasMetrics:

    longer_response_wins = 0
    different_lengths = 0

    predicted_labels = [
        _winner_to_label(winner)
        for winner in original_winners
    ]

    for delta, winner in zip(
        length_deltas,
        original_winners,
        strict=True,
    ):

        if delta == 0:
            continue

        different_lengths += 1

        longer_won = (
            delta > 0
            and winner == "A"
        ) or (
            delta < 0
            and winner == "B"
        )

        longer_response_wins += int(
            longer_won
        )

    correlation, correlation_reason = (
        _safe_pearson_correlation(
            length_deltas,
            predicted_labels,
        )
    )

    win_rate: float | None = None
    excess: float | None = None

    if different_lengths:

        win_rate = (
            longer_response_wins
            / different_lengths
        )

        excess = win_rate - 0.5

    bias_magnitude = (
        abs(excess)
        if excess is not None
        else None
    )

    severity = _verbosity_bias_severity(
        bias_magnitude
    )

    return VerbosityBiasMetrics(
        pairs_evaluated=len(length_deltas),
        pairs_with_different_lengths=(
            different_lengths
        ),
        longer_response_wins=(
            longer_response_wins
        ),
        longer_response_win_rate=win_rate,
        longer_response_win_rate_excess_over_chance=(
            excess
        ),
        length_delta_prediction_correlation=(
            correlation
        ),
        correlation_reason=correlation_reason,
        verbosity_bias_magnitude=(
            bias_magnitude
        ),
        bias_severity=severity,
    )


def _verbosity_bias_severity(
    magnitude: float | None,
) -> str:

    if magnitude is None:
        return "Unavailable"

    if magnitude <= 0.05:
        return "Low"

    if magnitude <= 0.15:
        return "Moderate"

    return "High"


def analyze_order_bias(
    original_winner: str,
    swapped_winner: str,
) -> BiasMitigationResult:
    """Analyze one pair under both response orderings.

    If the prediction flips correctly after swapping positions,
    the model is response-consistent.

    If it does not flip, confidence should be treated cautiously.
    """

    if original_winner not in {"A", "B"}:
        raise ValueError(
            "original_winner must be A or B."
        )

    if swapped_winner not in {"A", "B"}:
        raise ValueError(
            "swapped_winner must be A or B."
        )

    response_consistent = (
        swapped_winner
        == _opposite_winner(original_winner)
    )

    order_bias_detected = not response_consistent

    if response_consistent:
        debiased_winner = original_winner
        confidence_penalty = 0.0

    else:
        # When the model chooses the same position after swapping,
        # there is insufficient evidence to claim that one response
        # is genuinely preferred.
        debiased_winner = "Tie"
        confidence_penalty = 1.0

    return BiasMitigationResult(
        original_winner=original_winner,
        swapped_winner=swapped_winner,
        response_consistent=response_consistent,
        debiased_winner=debiased_winner,
        confidence_penalty=confidence_penalty,
        order_bias_detected=order_bias_detected,
    )


def calculate_debiased_probability(
    probability_original: float,
    probability_swapped_for_original: float,
) -> float:
    """Average two order-aware probabilities.

    ``probability_original``:
        Probability that Response A wins when shown first.

    ``probability_swapped_for_original``:
        Probability that the same Response A wins after positions
        are swapped.

    This gives an order-averaged estimate instead of trusting only
    one presentation order.
    """

    p1 = _validate_probability(
        probability_original
    )

    p2 = _validate_probability(
        probability_swapped_for_original
    )

    return (p1 + p2) / 2.0


def _validate_probability(
    value: float,
) -> float:

    try:
        value = float(value)

    except (TypeError, ValueError) as exc:

        raise ValueError(
            "Probability must be numeric."
        ) from exc

    if not math.isfinite(value):
        raise ValueError(
            "Probability must be finite."
        )

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "Probability must be between 0 and 1."
        )

    return value


def _safe_pearson_correlation(
    x_values: Sequence[int],
    y_values: Sequence[int],
) -> tuple[float | None, str | None]:

    if len(x_values) < 2:

        return (
            None,
            "Correlation requires at least two evaluation pairs.",
        )

    if len(set(x_values)) < 2:

        return (
            None,
            "Correlation is undefined because response-length "
            "deltas are constant.",
        )

    if len(set(y_values)) < 2:

        return (
            None,
            "Correlation is undefined because model predictions "
            "are constant.",
        )

    x_mean = (
        sum(x_values)
        / len(x_values)
    )

    y_mean = (
        sum(y_values)
        / len(y_values)
    )

    numerator = sum(
        (x - x_mean)
        * (y - y_mean)

        for x, y in zip(
            x_values,
            y_values,
            strict=True,
        )
    )

    x_sum_squares = sum(
        (x - x_mean) ** 2
        for x in x_values
    )

    y_sum_squares = sum(
        (y - y_mean) ** 2
        for y in y_values
    )

    denominator = math.sqrt(
        x_sum_squares
        * y_sum_squares
    )

    if denominator == 0:

        return (
            None,
            "Correlation is undefined because "
            "an input has no variance.",
        )

    return (
        float(numerator / denominator),
        None,
    )


def _validate_winner(
    winner: str,
    example_number: int,
    ordering: str,
) -> str:

    if winner not in {"A", "B"}:

        raise EvaluationPredictionError(
            f"{ordering.capitalize()} prediction for "
            f"example {example_number} returned "
            f"{winner!r}; expected only 'A' or 'B'."
        )

    return winner


def _validate_probability_b(
    score_b: float,
    example_number: int,
) -> float:

    try:
        probability_b = float(score_b)

    except (TypeError, ValueError) as exc:

        raise EvaluationPredictionError(
            f"Prediction for example {example_number} "
            "has an invalid score_b value."
        ) from exc

    if (
        not math.isfinite(probability_b)
        or not 0.0 <= probability_b <= 1.0
    ):

        raise EvaluationPredictionError(
            f"Prediction for example {example_number} "
            "has score_b outside [0, 1]."
        )

    return probability_b


def _winner_to_label(
    winner: str,
) -> int:

    return 0 if winner == "A" else 1


def _opposite_winner(
    winner: str,
) -> str:

    return "B" if winner == "A" else "A"