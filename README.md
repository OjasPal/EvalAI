# EvalAI

EvalAI is a local app that compares two AI responses and predicts which one a human is more likely to prefer.

This guide is written for beginners and teammates who are running the project for the first time.

## What You Will Get

With this repo, you can:
1. Enter a prompt.
2. Generate two responses from two different Ollama models.
3. Compare those responses with the trained RoBERTa reward model.
4. Save human feedback as A, B, or Tie.
5. Run held-out evaluation and bias checks.

## Architecture In One View

```text
Prompt
  -> Ollama model A (llama3.2) -> Response A
  -> Ollama model B (qwen2.5:3b) -> Response B
  -> FastAPI backend
  -> RoBERTa reward model scoring
  -> Predicted winner: A or B
```

## Before You Start

Install these first:
1. Python 3.10 or newer
2. Git
3. Ollama: https://ollama.com/download

Also make sure this model directory exists in your local repo:

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
cd C:\Users\HP\Downloads\test
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
cd C:\Users\HP\Downloads\test\EvalAI
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 3 (Frontend):

```powershell
cd C:\Users\HP\Downloads\test\EvalAI
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

## Common Beginner Errors And Fixes

### 1) Copy-Item says path not found

Cause: you are not in repo root.

Fix:

```powershell
cd C:\Users\HP\Downloads\test\EvalAI
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

## Notes For SI Project Usage

This repo is suitable for local SI project demonstration:
1. Core flows are implemented.
2. Tests and compile checks are available.
3. UI supports compare, feedback, and evaluation.

It is built for local/demo use, not internet-scale deployment.
