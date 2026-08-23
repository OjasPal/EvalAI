from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

try:
    from .preprocessing import load_feedback_examples
except ImportError:
    from preprocessing import load_feedback_examples


class PairwisePreferenceDataset(Dataset):

    def __init__(
        self,
        examples,
        tokenizer,
        max_length: int,
    ):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):

        example = self.examples[index]

        chosen_text = (
            f"{example.prompt}\n"
            f"Response: {example.chosen}"
        )

        rejected_text = (
            f"{example.prompt}\n"
            f"Response: {example.rejected}"
        )

        chosen = self.tokenizer(
            chosen_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        rejected = self.tokenizer(
            rejected_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        return {
            "chosen_input_ids": chosen[
                "input_ids"
            ].squeeze(0),

            "chosen_attention_mask": chosen[
                "attention_mask"
            ].squeeze(0),

            "rejected_input_ids": rejected[
                "input_ids"
            ].squeeze(0),

            "rejected_attention_mask": rejected[
                "attention_mask"
            ].squeeze(0),

            "preference_strength": torch.tensor(
                example.preference_strength,
                dtype=torch.float32,
            ),
        }


def pairwise_loss(
    chosen_reward: torch.Tensor,
    rejected_reward: torch.Tensor,
    preference_strength: torch.Tensor | None = None,
) -> torch.Tensor:

    per_example_loss = -torch.nn.functional.logsigmoid(
        chosen_reward - rejected_reward
    )

    if preference_strength is None:
        return per_example_loss.mean()

    return (
        per_example_loss * preference_strength
    ).mean()



def train(
    base_model: str,
    feedback_file: str,
    output_dir: str,
    max_length: int = 256,
    epochs: int = 1,
    batch_size: int = 4,
    learning_rate: float = 1e-5,
    max_feedback: int = 2000,
):

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    examples = load_feedback_examples(
        feedback_file,
        max_examples=max_feedback,
    )

    if len(examples) < 2:
        raise ValueError(
            "At least 2 trainable A/B human-feedback "
            "examples are required."
        )

    output_path = Path(output_dir)

    if output_path.exists():
        shutil.rmtree(output_path)

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    local_base = Path(base_model).is_dir()

    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        local_files_only=local_base,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        local_files_only=local_base,
    )

    model.to(device)
    model.train()

    dataset = PairwisePreferenceDataset(
        examples=examples,
        tokenizer=tokenizer,
        max_length=max_length,
    )

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
    )

    total_steps = 0

    for epoch in range(epochs):

        total_loss = 0.0

        for batch in loader:

            optimizer.zero_grad()

            chosen_ids = batch[
                "chosen_input_ids"
            ].to(device)

            chosen_mask = batch[
                "chosen_attention_mask"
            ].to(device)

            rejected_ids = batch[
                "rejected_input_ids"
            ].to(device)

            rejected_mask = batch[
                "rejected_attention_mask"
            ].to(device)

            preference_strength = batch[
                "preference_strength"
            ].to(device)

            chosen_reward = model(
                input_ids=chosen_ids,
                attention_mask=chosen_mask,
            ).logits.squeeze(-1)

            rejected_reward = model(
                input_ids=rejected_ids,
                attention_mask=rejected_mask,
            ).logits.squeeze(-1)

            loss = pairwise_loss(
                chosen_reward,
                rejected_reward,
                preference_strength,
            )

            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=1.0,
            )

            optimizer.step()

            total_loss += loss.item()
            total_steps += 1

        average_loss = (
            total_loss / max(len(loader), 1)
        )

        print(
            f"Epoch {epoch + 1}/{epochs} "
            f"- loss: {average_loss:.6f}"
        )

    model.eval()

    model.save_pretrained(
        output_path
    )

    tokenizer.save_pretrained(
        output_path
    )

    metadata = {
        "training_type": (
            "human_feedback_pairwise_finetuning"
        ),
        "feedback_examples": len(examples),
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "max_length": max_length,
        "device": device,
        "training_steps": total_steps,
        "base_model": str(base_model),
    }

    with (
        output_path / "training_metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
        )

    return metadata


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Fine-tune the EvalAI preference model "
            "using human A/B feedback."
        )
    )

    parser.add_argument(
        "--base-model",
        required=True,
    )

    parser.add_argument(
        "--feedback-file",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-5,
    )

    parser.add_argument(
        "--max-feedback",
        type=int,
        default=2000,
    )

    args = parser.parse_args()

    metadata = train(
        base_model=args.base_model,
        feedback_file=args.feedback_file,
        output_dir=args.output_dir,
        max_length=args.max_length,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_feedback=args.max_feedback,
    )

    print(
        json.dumps(
            metadata,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()