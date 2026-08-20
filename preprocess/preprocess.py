
import json
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split


# ============================================================
# Configuration
# ============================================================

DATASET_NAME = "lmarena-ai/arena-human-preference-55k"
SEED = 42

OUTPUT_DIR = Path("preprocess")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Convert list-like values into Python lists
# ============================================================

def to_list(value):
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return parsed

        except (json.JSONDecodeError, TypeError):
            pass

        return [value]

    return [str(value)]


# ============================================================
# Format prompt and responses
# ============================================================

def format_prompt(value):
    items = to_list(value)

    return "\n\n".join(
        f"User: {item}" for item in items
    )


def format_response(value):
    items = to_list(value)

    return "\n\n".join(
        str(item) for item in items
    )


# ============================================================
# Load dataset
# ============================================================

print("Loading dataset...")

dataset = load_dataset(DATASET_NAME)

df = dataset["train"].to_pandas()

print(f"Original rows: {len(df)}")


# ============================================================
# Remove ties
# ============================================================

tie_count = int(df["winner_tie"].sum())

df_clean = df[df["winner_tie"] == 0].copy()

print(f"Ties removed: {tie_count}")
print(f"Rows after removing ties: {len(df_clean)}")


# ============================================================
# Convert preference into binary label
#
# label = 0 -> response A preferred
# label = 1 -> response B preferred
# ============================================================

df_clean["label"] = np.where(
    df_clean["winner_model_a"] == 1,
    0,
    1
)


# ============================================================
# Keep only required columns
# ============================================================

df_clean = df_clean[
    ["prompt", "response_a", "response_b", "label"]
].copy()


# ============================================================
# Convert list strings into clean text
# ============================================================

df_clean["prompt"] = df_clean["prompt"].apply(format_prompt)

df_clean["response_a"] = df_clean["response_a"].apply(format_response)

df_clean["response_b"] = df_clean["response_b"].apply(format_response)


# ============================================================
# Remove missing / empty examples
# ============================================================

before = len(df_clean)

df_clean = df_clean.dropna(
    subset=["prompt", "response_a", "response_b", "label"]
)

df_clean = df_clean[
    (df_clean["prompt"].str.strip() != "") &
    (df_clean["response_a"].str.strip() != "") &
    (df_clean["response_b"].str.strip() != "")
]

print(f"Empty/invalid rows removed: {before - len(df_clean)}")


# ============================================================
# Remove duplicate preference examples
# ============================================================

before = len(df_clean)

df_clean = df_clean.drop_duplicates(
    subset=["prompt", "response_a", "response_b"]
).reset_index(drop=True)

print(f"Duplicate rows removed: {before - len(df_clean)}")


# ============================================================
# Randomly swap response A and B
#
# This prevents the model from learning that response A
# is always the preferred response.
# ============================================================

rng = np.random.default_rng(SEED)

swap_mask = rng.random(len(df_clean)) < 0.5

temp = df_clean.loc[swap_mask, "response_a"].copy()

df_clean.loc[swap_mask, "response_a"] = (
    df_clean.loc[swap_mask, "response_b"].values
)

df_clean.loc[swap_mask, "response_b"] = (
    temp.values
)

df_clean.loc[swap_mask, "label"] = (
    1 - df_clean.loc[swap_mask, "label"]
)


# ============================================================
# Shuffle dataset
# ============================================================

df_clean = df_clean.sample(
    frac=1,
    random_state=SEED
).reset_index(drop=True)


# ============================================================
# Train / validation / test split
#
# 80% train
# 10% validation
# 10% test
# ============================================================

train_df, temp_df = train_test_split(
    df_clean,
    test_size=0.20,
    random_state=SEED,
    stratify=df_clean["label"]
)

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=SEED,
    stratify=temp_df["label"]
)


# ============================================================
# Save CSV files
# ============================================================

train_df.to_csv(
    OUTPUT_DIR / "train.csv",
    index=False
)

val_df.to_csv(
    OUTPUT_DIR / "validation.csv",
    index=False
)

test_df.to_csv(
    OUTPUT_DIR / "test.csv",
    index=False
)


# ============================================================
# Final report
# ============================================================

print("\n========== PREPROCESSING COMPLETE ==========")

print(f"Final rows:       {len(df_clean)}")
print(f"Train rows:       {len(train_df)}")
print(f"Validation rows:  {len(val_df)}")
print(f"Test rows:        {len(test_df)}")

print("\nLabel distribution:")
print(df_clean["label"].value_counts())

print("\nLabel percentages:")
print(
    df_clean["label"]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)

print("\nOutput files:")
print(OUTPUT_DIR / "train.csv")
print(OUTPUT_DIR / "validation.csv")
print(OUTPUT_DIR / "test.csv")
