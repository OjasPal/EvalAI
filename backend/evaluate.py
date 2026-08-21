"""Run held-out preference-model evaluation from the project root.

Example:
    python -m backend.evaluate
    python -m backend.evaluate --limit 100
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .app.config import settings
from .app.model import PreferenceModel
from .app.model_utils import evaluate_preference_model


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the trained EvalAI RoBERTa preference model."
    )
    parser.add_argument(
        "--test-file",
        type=Path,
        default=settings.project_root / "preprocess" / "test.csv",
        help="Read-only held-out CSV (default: preprocess/test.csv).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional positive cap for a quick local check.",
    )
    return parser.parse_args()


def _summary_as_dict(summary: object) -> dict:
    # The public API uses Pydantic schemas.  This small command keeps its
    # stdout portable JSON without requiring a generated artifact on disk.
    from dataclasses import asdict

    return asdict(summary)


def main() -> int:
    args = _parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1.")

    model = PreferenceModel(settings)
    model.load()
    try:
        if model.demo_mode:
            raise RuntimeError(
                "Evaluation requires the trained RoBERTa checkpoint; "
                "set USE_DUMMY_MODEL=false."
            )
        summary = evaluate_preference_model(model, args.test_file, limit=args.limit)
        payload = {
            "dataset": str(args.test_file),
            "model": model.name,
            "demo_mode": model.demo_mode,
            **_summary_as_dict(summary),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    finally:
        model.unload()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
