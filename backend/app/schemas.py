from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    response_a: str = Field(..., min_length=1, max_length=30000)
    response_b: str = Field(..., min_length=1, max_length=30000)

    @field_validator("prompt", "response_a", "response_b")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be empty.")
        return value


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be empty.")
        return value


class GenerateResponse(BaseModel):
    response_a: str
    response_b: str
    model_a: str
    model_b: str


class PredictResponse(BaseModel):
    request_id: str
    winner: Literal["A", "B"]
    score_a: float = Field(..., ge=0.0, le=1.0)
    score_b: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model: str
    demo_mode: bool


class FeedbackRequest(BaseModel):
    request_id: str | None = None
    prompt: str = Field(..., min_length=1, max_length=12000)
    response_a: str = Field(..., min_length=1, max_length=30000)
    response_b: str = Field(..., min_length=1, max_length=30000)
    human_preference: Literal["A", "B", "Tie"]

    @field_validator("prompt", "response_a", "response_b")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be empty.")
        return value


class FeedbackResponse(BaseModel):
    status: Literal["saved"]
    feedback_id: str


class EvaluationRequest(BaseModel):
    """Optional cap is useful for a quick local smoke test of the evaluator."""

    limit: int | None = Field(default=None, ge=1, le=100000)


class ClassMetricsResponse(BaseModel):
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    support: int = Field(..., ge=0)


class EvaluationMetricsResponse(BaseModel):
    """Metrics use label 0 for A preferred and label 1 for B preferred."""

    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    roc_auc: float | None = Field(default=None, ge=0.0, le=1.0)
    roc_auc_reason: str | None = None
    confusion_matrix: list[list[int]]
    class_metrics: dict[str, ClassMetricsResponse]


class PositionBiasResponse(BaseModel):
    """A consistent swap changes the winner from A to B, or B to A."""

    pairs_evaluated: int = Field(..., ge=1)
    consistent_swaps: int = Field(..., ge=0)
    inconsistent_swaps: int = Field(..., ge=0)
    consistent_swap_rate: float = Field(..., ge=0.0, le=1.0)
    inconsistent_swap_rate: float = Field(..., ge=0.0, le=1.0)
    original_first_position_win_rate: float = Field(..., ge=0.0, le=1.0)
    swapped_first_position_win_rate: float = Field(..., ge=0.0, le=1.0)
    combined_first_position_win_rate: float = Field(..., ge=0.0, le=1.0)


class VerbosityBiasResponse(BaseModel):
    """Negative length/prediction correlation indicates a longer-response tendency."""

    pairs_evaluated: int = Field(..., ge=1)
    pairs_with_different_lengths: int = Field(..., ge=0)
    longer_response_wins: int = Field(..., ge=0)
    longer_response_win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    longer_response_win_rate_excess_over_chance: float | None = Field(
        default=None, ge=-0.5, le=0.5
    )
    length_delta_prediction_correlation: float | None = Field(
        default=None, ge=-1.0, le=1.0
    )
    correlation_reason: str | None = None


class EvaluationResponse(BaseModel):
    dataset: str
    model: str
    demo_mode: bool
    examples_evaluated: int = Field(..., ge=1)
    metrics: EvaluationMetricsResponse
    position_bias: PositionBiasResponse
    verbosity_bias: VerbosityBiasResponse
