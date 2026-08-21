# EvalAI

## Smart India Hackathon Project

EvalAI is an explainable human-preference evaluation platform for competing large language model (LLM) responses. It generates two answers for the same prompt, uses a trained RoBERTa reward model to predict the preferred response, and combines that prediction with human feedback and evaluation diagnostics.

This repository contains the working prototype for our Smart India Hackathon (SIH) project. It is designed as a local-first demonstration that makes LLM response quality easier to compare, review, and analyze.

## Problem Statement

Different LLMs can produce very different answers to the same prompt. Comparing those answers manually is slow, subjective, and difficult to reproduce. A useful evaluation workflow should:

- Compare responses under the same prompt.
- Provide a consistent model-based preference signal.
- Keep a human evaluator in the loop.
- Measure performance on held-out data.
- Surface potential position and verbosity bias.

## Our Solution

EvalAI creates a complete comparison loop:

1. A user enters a prompt.
2. Two locally hosted Ollama models generate competing responses.
3. A trained RoBERTa reward model scores both responses.
4. The system predicts whether Response A or Response B is preferred.
5. A human evaluator can submit A, B, or Tie feedback.
6. Held-out evaluation and bias checks measure model behavior.

The result is a practical evaluation interface rather than a single opaque score.

## Key Features

- **Side-by-side response generation:** Generate two answers from the same prompt.
- **Preference prediction:** Use the trained RoBERTa model to rank the responses.
- **Human review:** Record human preference as A, B, or Tie.
- **Held-out evaluation:** Measure accuracy, precision, recall, F1-score, and ROC-AUC.
- **Bias diagnostics:** Check sensitivity to response order and answer verbosity.
- **Local and private workflow:** Run the application with local models and local data.
- **Interactive dashboard:** Use the Streamlit interface to compare, review, and inspect results.

## System Architecture

```text
User prompt
    |
    +--> Ollama model A (llama3.2) ----> Response A --+
    |                                                  |
    +--> Ollama model B (qwen2.5:3b) -> Response B --+--> FastAPI backend
                                                       |
                                                       +--> RoBERTa reward model
                                                       |
                                                       +--> Predicted winner: A or B
                                                       |
                                                       +--> Human feedback and diagnostics
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| User interface | Streamlit |
| Application API | FastAPI and Uvicorn |
| Preference model | Fine-tuned RoBERTa reward model |
| Local response generation | Ollama with `llama3.2` and `qwen2.5:3b` |
| Data and feedback | CSV, JSONL, and local model artifacts |
| Testing | Python `unittest`, compilation checks |

## Demonstration Flow

1. Open the **Compare** tab.
2. Enter a prompt and generate two responses, or paste responses manually.
3. Select **Compare Responses** to view scores, confidence, and the predicted winner.
4. Open **Human Feedback** and record your preference.
5. Open **Evaluation & Bias** to run benchmark and diagnostic checks.
6. Use the **About** tab to confirm backend and model readiness.

## Project Structure

```text
EvalAI/
├── backend/                 # FastAPI application, routes, model, and storage
│   ├── app/
│   ├── data/
│   └── tests/
├── frontend/                # Streamlit dashboard and theme configuration
├── notebooks/               # Dataset inspection and model artifacts
├── preprocess/              # Dataset preprocessing and data splits
├── src/                     # Training, inference, preprocessing, and evaluation
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10 or newer
- Git
- Ollama: https://ollama.com/download
- The trained model directory at `notebooks/roberta_reward_model_FINAL`

## Before You Start

Make sure the trained model directory exists in the repository:

```text
notebooks/roberta_reward_model_FINAL
```

That folder should include at least:

```text
config.json
model.safetensors
tokenizer.json
tokenizer_config.json
```

## Quick Start (Windows PowerShell)

Run these commands in order.

```powershell
cd <parent-directory>
git clone <your-repo-url>
cd EvalAI

python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env

ollama pull llama3.2
ollama pull qwen2.5:3b
```

Now start services in separate terminals.

Terminal 1 (Ollama):

```powershell
ollama serve
```

Terminal 2 (Backend):

```powershell
cd <project-directory>\EvalAI
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 3 (Frontend):

```powershell
cd <project-directory>\EvalAI
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/app.py --server.port 8502
```

Open the app:

```text
http://localhost:8502
```

## Quick Start (macOS/Linux)

```bash
git clone <your-repo-url>
cd EvalAI

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

ollama pull llama3.2
ollama pull qwen2.5:3b
```

Then start:
1. ollama serve
2. python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
3. python -m streamlit run frontend/app.py --server.port 8502

## First Run Checklist

After startup, confirm these URLs:
1. Backend health: http://127.0.0.1:8000/health
2. Backend docs: http://127.0.0.1:8000/docs
3. Frontend app: http://localhost:8502

Healthy backend should return status ok.

## How To Use The App

1. Open the Compare tab.
2. Enter your prompt.
3. Click Generate two responses.
4. Click Compare responses.
5. Review winner and confidence.
6. Open Human Feedback tab and submit A, B, or Tie.
7. Open Evaluation and Bias tab when you want benchmark metrics.

## Important Project Rules

1. Do not edit notebooks or preprocess folders for normal app usage.
2. Keep backend/.env and frontend/.env local only.
3. Do not put secrets in .env.example files.
4. Feedback is saved locally at backend/data/feedback.jsonl.

## Config Reference

Main backend settings in backend/.env:

```env
USE_DUMMY_MODEL=false
MODEL_PATH=notebooks/roberta_reward_model_FINAL
MODEL_LABEL_MAPPING=A,B
MAX_LENGTH=256
OLLAMA_URL=http://127.0.0.1:11434
GENERATION_MODEL_A=llama3.2
GENERATION_MODEL_B=qwen2.5:3b
GENERATION_TIMEOUT=120
CORS_ORIGINS=*
```

Frontend setting in frontend/.env:

```env
BACKEND_URL=http://127.0.0.1:8000
```

## API Endpoints

1. GET /health: backend and model status
2. POST /generate: generate response A and response B
3. POST /predict: score both responses and return winner A or B
4. POST /feedback: save human preference
5. POST /evaluation: run held-out benchmark and bias checks

## Validation Commands

Run these from project root:

```bash
python -m unittest discover -s backend/tests -t backend -v
python -m compileall -q backend frontend
```

## Troubleshooting

### 1) Copy-Item says path not found

Cause: you are not in repo root.

Fix:

```powershell
cd <project-directory>\EvalAI
Copy-Item backend\.env.example backend\.env
```

### 2) Frontend shows backend offline

Fix checklist:
1. Backend terminal is running uvicorn.
2. Health URL opens: http://127.0.0.1:8000/health
3. frontend/.env has correct BACKEND_URL.

### 3) Generate fails because Ollama is unavailable

Fix:

```bash
ollama serve
ollama list
ollama pull llama3.2
ollama pull qwen2.5:3b
```

### 4) Evaluation takes long

This is normal. Evaluation runs the held-out test set and additional bias checks.

## Data, Privacy, and Scope

- Response generation runs through locally hosted Ollama models.
- Human feedback is stored locally at `backend/data/feedback.jsonl`.
- The prototype is intended for local evaluation and demonstration.
- The current implementation is not positioned as an internet-scale production service.
- Do not commit local `.env` files, credentials, or private datasets.

## Limitations

- Preference quality depends on the training data and reward model.
- Held-out evaluation can take several minutes on CPU.
- Ollama must be running and both configured generation models must be available.
- A model prediction is a decision-support signal, not a replacement for human judgment.

## Future Scope

- Add authentication and role-based evaluator access.
- Support additional generation providers and reward models.
- Add persistent experiment tracking and richer result visualizations.
- Expand multilingual evaluation and domain-specific benchmarks.
- Add deployment support for shared team or institutional environments.

## License

This project is distributed under the license included in `LICENSE`.
