import json
from pathlib import Path
from uuid import uuid4

from .schemas import FeedbackRequest


def save_feedback(feedback: FeedbackRequest, file_path: str) -> str:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    feedback_id = str(uuid4())
    record = {
        "feedback_id": feedback_id,
        **feedback.model_dump(),
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return feedback_id
