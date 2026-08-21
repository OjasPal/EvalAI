from uuid import uuid4

from fastapi import APIRouter, HTTPException

from .config import settings
from .generation import generate_responses
from .model import PreferenceModel
from .model_utils import (
    EvaluationDataError,
    EvaluationPredictionError,
    evaluate_preference_model,
)
from .schemas import (
    ClassMetricsResponse,
    EvaluationMetricsResponse,
    EvaluationRequest,
    EvaluationResponse,
    FeedbackRequest,
    FeedbackResponse,
    GenerateRequest,
    GenerateResponse,
    PositionBiasResponse,
    PredictRequest,
    PredictResponse,
    VerbosityBiasResponse,
)
from .storage import save_feedback

router = APIRouter()

_model: PreferenceModel | None = None


def set_model(model: PreferenceModel) -> None:
    global _model
    _model = model


@router.get("/")
def root() -> dict[str, str]:
    return {
        "service": "EvalAI preference prediction API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health() -> dict:
    if _model is None:
        return {"status": "starting", "demo_mode": False, "model": None, "error": None}

    if _model.load_error:
        return {
            "status": "degraded",
            "model": _model.name,
            "demo_mode": _model.demo_mode,
            "device": _model.device,
            "error": _model.load_error,
        }

    return {
        "status": "ok",
        "model": _model.name,
        "demo_mode": _model.demo_mode,
        "device": _model.device,
        "error": None,
    }


@router.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    if _model is None:
        raise HTTPException(status_code=503, detail="Model is not ready.")
    if _model.load_error:
        raise HTTPException(
            status_code=503,
            detail=f"Model is unavailable: {_model.load_error}",
        )

    try:
        result = _model.predict(
            prompt=payload.prompt,
            response_a=payload.response_a,
            response_b=payload.response_b,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {exc}",
        ) from exc

    winner = result.winner
    if winner not in {"A", "B"}:
        raise HTTPException(status_code=500, detail="Model returned an invalid winner.")

    return PredictResponse(
        request_id=str(uuid4()),
        winner=winner,
        score_a=round(result.score_a, 6),
        score_b=round(result.score_b, 6),
        confidence=round(result.confidence, 6),
        model=_model.name,
        demo_mode=_model.demo_mode,
    )


@router.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest) -> GenerateResponse:
    try:
        response_a, response_b = generate_responses(payload.prompt, settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return GenerateResponse(
        response_a=response_a,
        response_b=response_b,
        model_a=settings.generation_model_a,
        model_b=settings.generation_model_b,
    )


@router.post("/evaluation", response_model=EvaluationResponse)
def evaluate(payload: EvaluationRequest) -> EvaluationResponse:
    """Evaluate the trained model against the read-only held-out test CSV."""

    if _model is None:
        raise HTTPException(status_code=503, detail="Model is not ready.")
    if _model.load_error:
        raise HTTPException(
            status_code=503,
            detail=f"Evaluation requires an available model: {_model.load_error}",
        )
    if _model.demo_mode:
        raise HTTPException(
            status_code=503,
            detail="Evaluation requires the trained RoBERTa model; dummy mode is active.",
        )

    test_file = settings.project_root / "preprocess" / "test.csv"
    try:
        summary = evaluate_preference_model(_model, test_file, limit=payload.limit)
    except (EvaluationDataError, EvaluationPredictionError) as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc

    metrics = summary.metrics
    position_bias = summary.position_bias
    verbosity_bias = summary.verbosity_bias
    return EvaluationResponse(
        dataset="preprocess/test.csv",
        model=_model.name,
        demo_mode=_model.demo_mode,
        examples_evaluated=summary.examples_evaluated,
        metrics=EvaluationMetricsResponse(
            accuracy=metrics.accuracy,
            precision=metrics.precision,
            recall=metrics.recall,
            f1=metrics.f1,
            roc_auc=metrics.roc_auc,
            roc_auc_reason=metrics.roc_auc_reason,
            confusion_matrix=metrics.confusion_matrix,
            class_metrics={
                label: ClassMetricsResponse(**values)
                for label, values in metrics.class_metrics.items()
            },
        ),
        position_bias=PositionBiasResponse(
            pairs_evaluated=position_bias.pairs_evaluated,
            consistent_swaps=position_bias.consistent_swaps,
            inconsistent_swaps=position_bias.inconsistent_swaps,
            consistent_swap_rate=position_bias.consistent_swap_rate,
            inconsistent_swap_rate=position_bias.inconsistent_swap_rate,
            original_first_position_win_rate=position_bias.original_first_position_win_rate,
            swapped_first_position_win_rate=position_bias.swapped_first_position_win_rate,
            combined_first_position_win_rate=position_bias.combined_first_position_win_rate,
        ),
        verbosity_bias=VerbosityBiasResponse(
            pairs_evaluated=verbosity_bias.pairs_evaluated,
            pairs_with_different_lengths=verbosity_bias.pairs_with_different_lengths,
            longer_response_wins=verbosity_bias.longer_response_wins,
            longer_response_win_rate=verbosity_bias.longer_response_win_rate,
            longer_response_win_rate_excess_over_chance=(
                verbosity_bias.longer_response_win_rate_excess_over_chance
            ),
            length_delta_prediction_correlation=(
                verbosity_bias.length_delta_prediction_correlation
            ),
            correlation_reason=verbosity_bias.correlation_reason,
        ),
    )


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest) -> FeedbackResponse:
    try:
        feedback_id = save_feedback(payload, settings.feedback_file)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save feedback: {exc}",
        ) from exc

    return FeedbackResponse(status="saved", feedback_id=feedback_id)
