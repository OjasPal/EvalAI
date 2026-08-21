from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings


@dataclass
class Prediction:
    score_a: float
    score_b: float
    winner: str
    confidence: float


class PreferenceModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        self.demo_mode = settings.use_dummy_model
        self.load_error: str | None = None

    @property
    def labels(self) -> tuple[str, ...]:
        return self.settings.model_label_mapping or ("A", "B")

    def load(self) -> None:
        self.load_error = None
        if self.settings.use_dummy_model or not self.settings.model_path.strip():
            self.demo_mode = True
            self.model = None
            self.tokenizer = None
            return

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_id = self.settings.model_path.strip()
        model_path = Path(model_id)
        if not model_path.is_absolute():
            model_path = self.settings.project_root / model_path
        model_id = str(model_path)
        local_checkpoint = model_path.is_dir()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            if local_checkpoint and not (model_path / "config.json").exists():
                raise FileNotFoundError(
                    f"Local model directory is missing config.json: {model_path}"
                )

            load_options = {"local_files_only": local_checkpoint}
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_id, **load_options)
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_id, use_fast=False, **load_options
                )

            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_id,
                **load_options,
            )
            self.model.to(self.device)
            self.model.eval()
            self.demo_mode = False
            self.load_error = None
        except Exception as exc:  # pragma: no cover - runtime guard for missing checkpoint
            self.model = None
            self.tokenizer = None
            self.demo_mode = False
            self.load_error = f"Reward model failed to load: {exc}"

    def unload(self) -> None:
        self.tokenizer = None
        self.model = None
        self.load_error = None

    @staticmethod
    def _dummy_prediction(response_a: str, response_b: str) -> Prediction:
        # Placeholder only. Do not present these numbers as trained-model metrics.
        len_a = max(len(response_a), 1)
        len_b = max(len(response_b), 1)
        raw_a = 1.0 + min(len_a / len_b, 2.0) * 0.05
        raw_b = 1.0 + min(len_b / len_a, 2.0) * 0.05
        score_a = raw_a / (raw_a + raw_b)
        score_b = 1.0 - score_a
        # The application contract is strictly binary.  Match trained-model
        # inference by resolving an exact score tie in favour of Response A.
        winner = "A" if score_a >= score_b else "B"
        confidence = max(score_a, score_b)
        return Prediction(score_a, score_b, winner, confidence)

    def _build_text(self, prompt: str, response: str) -> str:
        return f"{prompt}\nResponse: {response}"

    def predict(self, prompt: str, response_a: str, response_b: str) -> Prediction:
        if self.demo_mode:
            return self._dummy_prediction(response_a, response_b)

        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Preference model is not loaded.")

        import torch

        encoded_a = self.tokenizer(
            self._build_text(prompt, response_a),
            return_tensors="pt",
            truncation=True,
            max_length=self.settings.max_length,
            padding=False,
        )
        encoded_b = self.tokenizer(
            self._build_text(prompt, response_b),
            return_tensors="pt",
            truncation=True,
            max_length=self.settings.max_length,
            padding=False,
        )
        encoded_a = {key: value.to(self.device) for key, value in encoded_a.items()}
        encoded_b = {key: value.to(self.device) for key, value in encoded_b.items()}

        with torch.inference_mode():
            reward_a = self.model(**encoded_a).logits.squeeze().item()
            reward_b = self.model(**encoded_b).logits.squeeze().item()

        probability_a = torch.sigmoid(torch.tensor(reward_a - reward_b)).item()
        probability_b = 1.0 - probability_a
        if probability_a >= probability_b:
            winner = "A"
            confidence = probability_a
        else:
            winner = "B"
            confidence = probability_b

        return Prediction(
            score_a=probability_a,
            score_b=probability_b,
            winner=winner,
            confidence=confidence,
        )

    @property
    def name(self) -> str:
        if self.demo_mode:
            return "dummy-demo-model"
        return self.settings.model_path
