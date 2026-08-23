from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


DIMENSIONS = (
    "helpfulness",
    "correctness",
    "relevance",
    "clarity",
    "safety",
)


@dataclass(frozen=True)
class PreferenceExample:
    prompt: str
    chosen: str
    rejected: str
    preference_strength: float = 1.0


def load_feedback(
    path: str | Path,
) -> list[dict]:

    path = Path(path)

    if not path.exists():
        return []

    records: list[dict] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(record, dict):
                records.append(record)

    return records


def _dimension_score(
    record: dict,
    response: str,
) -> float:
    suffix = response.lower()
    values = []

    for dimension in DIMENSIONS:
        value = record.get(f"{dimension}_{suffix}", 3)

        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 3.0

        values.append(max(1.0, min(5.0, value)))

    return sum(values) / len(values)


def _preference_strength(
    chosen_score: float,
    rejected_score: float,
) -> float:
    # Keep the original pairwise objective intact while giving
    # stronger human-rated differences a proportionally stronger signal.
    difference = abs(chosen_score - rejected_score)
    return 1.0 + (difference / 4.0)


def build_preference_examples(
    records: list[dict],
) -> list[PreferenceExample]:

    examples: list[PreferenceExample] = []

    for record in records:
        preference = record.get("human_preference")

        if preference == "A":
            chosen = record.get("response_a")
            rejected = record.get("response_b")
            chosen_score = _dimension_score(record, "a")
            rejected_score = _dimension_score(record, "b")

        elif preference == "B":
            chosen = record.get("response_b")
            rejected = record.get("response_a")
            chosen_score = _dimension_score(record, "b")
            rejected_score = _dimension_score(record, "a")

        else:
            # Tie remains excluded from the binary pairwise objective.
            continue

        prompt = record.get("prompt")

        if not prompt or not chosen or not rejected:
            continue

        examples.append(
            PreferenceExample(
                prompt=prompt.strip(),
                chosen=chosen.strip(),
                rejected=rejected.strip(),
                preference_strength=_preference_strength(
                    chosen_score,
                    rejected_score,
                ),
            )
        )

    return examples


def load_feedback_examples(
    path: str | Path,
    max_examples: int | None = None,
) -> list[PreferenceExample]:

    records = load_feedback(path)

    examples = build_preference_examples(records)

    if max_examples is not None:
        examples = examples[-max_examples:]

    return examples