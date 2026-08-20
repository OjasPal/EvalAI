import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "roberta_reward_model_FINAL")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

def predict_preference(prompt, response_a, response_b):
    text_a = f"{prompt}\nResponse: {response_a}"
    text_b = f"{prompt}\nResponse: {response_b}"
    inputs_a = tokenizer(text_a, return_tensors="pt", truncation=True, max_length=256).to(device)
    inputs_b = tokenizer(text_b, return_tensors="pt", truncation=True, max_length=256).to(device)
    with torch.no_grad():
        reward_a = model(**inputs_a).logits.squeeze().item()
        reward_b = model(**inputs_b).logits.squeeze().item()
    probability_a = torch.sigmoid(torch.tensor(reward_a - reward_b)).item()
    probability_b = 1 - probability_a
    preference = "Response A" if probability_a >= probability_b else "Response B"
    return {"reward_a": reward_a, "reward_b": reward_b,
            "probability_a": probability_a, "probability_b": probability_b,
            "preference": preference}