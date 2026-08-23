import json
from pathlib import Path
from uuid import uuid4

from .schemas import FeedbackRequest


def save_feedback(
    feedback: FeedbackRequest,
    file_path: str,
) -> str:

    path = Path(file_path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    feedback_id = str(uuid4())

    record = {
        "feedback_id": feedback_id,
        **feedback.model_dump(),
    }

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )

    return feedback_id


def load_feedback(
    file_path: str,
) -> list[dict]:

    path = Path(file_path)

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


def load_trainable_feedback(
    file_path: str,
    max_examples: int | None = None,
) -> list[dict]:

    records = load_feedback(file_path)

    trainable = [
        record
        for record in records
        if record.get("human_preference") in {"A", "B"}
    ]

    if max_examples is not None:
        trainable = trainable[-max_examples:]

    return trainable


def feedback_count(
    file_path: str,
) -> int:

    return len(
        load_trainable_feedback(file_path)
    )