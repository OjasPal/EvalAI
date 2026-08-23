from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Literal, cast
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
    RetrainRequest,
    RetrainResponse,
    VerbosityBiasResponse,
)
from .storage import (
    feedback_count,
    save_feedback,
)


router = APIRouter()

_model: PreferenceModel | None = None


def set_model(
    model: PreferenceModel,
) -> None:

    global _model
    _model = model


def _evaluate_model(
    model: PreferenceModel,
):
    test_file = (
        settings.project_root
        / "preprocess"
        / "test.csv"
    )

    return evaluate_preference_model(
        model,
        test_file,
        limit=None,
    )


def _is_candidate_better(
    current_summary,
    candidate_summary,
) -> bool:

    current_metrics = current_summary.metrics
    candidate_metrics = candidate_summary.metrics

    # Primary quality metrics must not decrease.
    if candidate_metrics.accuracy < current_metrics.accuracy:
        return False

    if candidate_metrics.f1 < current_metrics.f1:
        return False

    # If both have ROC-AUC, don't allow it to decrease.
    if (
        current_metrics.roc_auc is not None
        and candidate_metrics.roc_auc is not None
        and candidate_metrics.roc_auc
        < current_metrics.roc_auc
    ):
        return False

    # Do not allow position inconsistency to increase.
    if (
        candidate_summary.position_bias.inconsistent_swap_rate
        > current_summary.position_bias.inconsistent_swap_rate
    ):
        return False

    return (
        candidate_metrics.accuracy
        > current_metrics.accuracy
        or candidate_metrics.f1
        > current_metrics.f1
        or (
            candidate_metrics.roc_auc is not None
            and current_metrics.roc_auc is not None
            and candidate_metrics.roc_auc
            > current_metrics.roc_auc
        )
    )


@router.get("/")
def root() -> dict[str, str]:

    return {
        "service": (
            "EvalAI preference prediction API"
        ),
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health() -> dict:

    if _model is None:
        return {
            "status": "starting",
            "demo_mode": False,
            "model": None,
            "error": None,
        }

    if not _model.demo_mode and _model.model is None and not _model.load_error:
        return {
            "status": "starting",
            "model": _model.name,
            "demo_mode": False,
            "device": _model.device,
            "error": None,
        }

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


@router.post(
    "/predict",
    response_model=PredictResponse,
)
def predict(
    payload: PredictRequest,
) -> PredictResponse:

    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not ready.",
        )

    if _model.load_error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Model is unavailable: "
                f"{_model.load_error}"
            ),
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
        raise HTTPException(
            status_code=500,
            detail=(
                "Model returned an invalid winner."
            ),
        )

    validated_winner = cast(Literal["A", "B"], winner)

    return PredictResponse(
        request_id=str(uuid4()),
        winner=validated_winner,
        score_a=round(
            result.score_a,
            6,
        ),
        score_b=round(
            result.score_b,
            6,
        ),
        confidence=round(
            result.confidence,
            6,
        ),
        model=_model.name,
        demo_mode=_model.demo_mode,
    )


@router.post(
    "/generate",
    response_model=GenerateResponse,
)
def generate(
    payload: GenerateRequest,
) -> GenerateResponse:

    try:
        response_a, response_b = generate_responses(
            payload.prompt,
            settings,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return GenerateResponse(
        response_a=response_a,
        response_b=response_b,
        model_a=settings.generation_model_a,
        model_b=settings.generation_model_b,
    )


@router.post(
    "/evaluation",
    response_model=EvaluationResponse,
)
def evaluate(
    payload: EvaluationRequest,
) -> EvaluationResponse:

    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not ready.",
        )

    if _model.load_error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Evaluation requires an available model: "
                f"{_model.load_error}"
            ),
        )

    if _model.demo_mode:
        raise HTTPException(
            status_code=503,
            detail=(
                "Evaluation requires the trained "
                "RoBERTa model; dummy mode is active."
            ),
        )

    test_file = (
        settings.project_root
        / "preprocess"
        / "test.csv"
    )

    try:
        summary = evaluate_preference_model(
            _model,
            test_file,
            limit=payload.limit,
        )

    except (
        EvaluationDataError,
        EvaluationPredictionError,
    ) as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {exc}",
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {exc}",
        ) from exc

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
                label: ClassMetricsResponse(
                    precision=values["precision"],
                    recall=values["recall"],
                    f1=values["f1"],
                    support=int(values["support"]),
                )
                for label, values
                in metrics.class_metrics.items()
            },
        ),

        position_bias=PositionBiasResponse(
            pairs_evaluated=position_bias.pairs_evaluated,
            consistent_swaps=position_bias.consistent_swaps,
            inconsistent_swaps=position_bias.inconsistent_swaps,
            consistent_swap_rate=position_bias.consistent_swap_rate,
            inconsistent_swap_rate=position_bias.inconsistent_swap_rate,
            original_first_position_win_rate=(
                position_bias.original_first_position_win_rate
            ),
            swapped_first_position_win_rate=(
                position_bias.swapped_first_position_win_rate
            ),
            combined_first_position_win_rate=(
                position_bias.combined_first_position_win_rate
            ),
        ),

        verbosity_bias=VerbosityBiasResponse(
            pairs_evaluated=verbosity_bias.pairs_evaluated,
            pairs_with_different_lengths=(
                verbosity_bias.pairs_with_different_lengths
            ),
            longer_response_wins=(
                verbosity_bias.longer_response_wins
            ),
            longer_response_win_rate=(
                verbosity_bias.longer_response_win_rate
            ),
            longer_response_win_rate_excess_over_chance=(
                verbosity_bias
                .longer_response_win_rate_excess_over_chance
            ),
            length_delta_prediction_correlation=(
                verbosity_bias
                .length_delta_prediction_correlation
            ),
            correlation_reason=(
                verbosity_bias.correlation_reason
            ),
        ),
    )


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
)
def feedback(
    payload: FeedbackRequest,
) -> FeedbackResponse:

    try:
        feedback_id = save_feedback(
            payload,
            settings.feedback_file,
        )

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not save feedback: {exc}"
            ),
        ) from exc

    return FeedbackResponse(
        status="saved",
        feedback_id=feedback_id,
    )


@router.post(
    "/retrain",
    response_model=RetrainResponse,
)
def retrain(
    payload: RetrainRequest,
) -> RetrainResponse:

    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="Model is not ready.",
        )

    if _model.load_error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Current model is unavailable: "
                f"{_model.load_error}"
            ),
        )

    if _model.demo_mode:
        raise HTTPException(
            status_code=503,
            detail=(
                "Retraining requires the trained "
                "RoBERTa model."
            ),
        )

    minimum = (
        payload.min_feedback
        if payload.min_feedback is not None
        else settings.min_feedback_for_retrain
    )

    available = feedback_count(
        settings.feedback_file
    )

    if available < minimum:
        return RetrainResponse(
            status="rejected",
            message=(
                f"Need at least {minimum} trainable "
                f"A/B feedback examples; only "
                f"{available} are available."
            ),
            feedback_examples=available,
            model=_model.name,
        )

    project_root = settings.project_root

    candidate_dir = (
        Path(settings.models_dir)
        / "v2_candidate"
    )

    candidate_dir.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Keep the current model untouched.
    base_model_path = Path(
        _model.active_model_path
    )

    if not base_model_path.is_absolute():
        base_model_path = (
            project_root
            / base_model_path
        )

    command = [
        sys.executable,
        str(
            project_root
            / "src"
            / "feedback_training.py"
        ),

        "--base-model",
        str(base_model_path.resolve()),

        "--feedback-file",
        str(
            Path(
                settings.feedback_file
            ).resolve()
        ),

        "--output-dir",
        str(
            candidate_dir.resolve()
        ),

        "--max-length",
        str(settings.max_length),

        "--epochs",
        str(settings.training_epochs),

        "--batch-size",
        str(settings.training_batch_size),

        "--learning-rate",
        str(
            settings.training_learning_rate
        ),

        "--max-feedback",
        str(
            settings.training_max_feedback
        ),
    ]

    try:

        result = subprocess.run(
            command,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )

        if result.returncode != 0:

            return RetrainResponse(
                status="failed",
                message=(
                    "Training failed:\n"
                    + (
                        result.stderr[-4000:]
                        or result.stdout[-4000:]
                        or "Unknown training error."
                    )
                ),
                feedback_examples=available,
                model=_model.name,
            )

        if not candidate_dir.is_dir():
            return RetrainResponse(
                status="failed",
                message=(
                    "Training completed but "
                    "candidate model was not created."
                ),
                feedback_examples=available,
                model=_model.name,
            )

        # -----------------------------
        # Evaluate current model
        # -----------------------------

        current_summary = _evaluate_model(
            _model
        )

        # -----------------------------
        # Load candidate separately
        # -----------------------------

        candidate_settings = replace(
            settings,
            model_path=str(
                candidate_dir.resolve()
            ),
            use_dummy_model=False,
        )

        candidate_model = PreferenceModel(
            candidate_settings
        )

        candidate_model.load()

        if candidate_model.load_error:
            return RetrainResponse(
                status="failed",
                message=(
                    "Candidate model could not "
                    "be loaded. Current model "
                    "was kept unchanged.\n"
                    + candidate_model.load_error
                ),
                feedback_examples=available,
                model=_model.name,
            )

        candidate_summary = _evaluate_model(
            candidate_model
        )

        # -----------------------------
        # Safety gate
        # -----------------------------

        if not _is_candidate_better(
            current_summary,
            candidate_summary,
        ):

            shutil.rmtree(
                candidate_dir,
                ignore_errors=True,
            )

            return RetrainResponse(
                status="rejected",
                message=(
                    "Candidate model did not "
                    "outperform the current model. "
                    "Current model remains active."
                ),
                feedback_examples=available,
                model=_model.name,
            )

        # -----------------------------
        # Candidate is better.
        # Activate it.
        # -----------------------------

        _model.reload_from_path(
            str(candidate_dir)
        )

        return RetrainResponse(
            status="completed",
            message=(
                "Human-feedback model improved "
                "on the held-out evaluation and "
                "was activated successfully."
            ),
            feedback_examples=available,
            model=_model.name,
        )

    except subprocess.TimeoutExpired:

        return RetrainResponse(
            status="failed",
            message=(
                "Training timed out after "
                "60 minutes. Current model "
                "remains active."
            ),
            feedback_examples=available,
            model=_model.name,
        )

    except (
        EvaluationDataError,
        EvaluationPredictionError,
    ) as exc:

        return RetrainResponse(
            status="failed",
            message=(
                "Candidate evaluation failed. "
                "Current model remains active. "
                f"Details: {exc}"
            ),
            feedback_examples=available,
            model=_model.name,
        )

    except Exception as exc:

        return RetrainResponse(
            status="failed",
            message=(
                "Retraining failed. Current "
                f"model remains active. Details: {exc}"
            ),
            feedback_examples=available,
            model=_model.name,
        )