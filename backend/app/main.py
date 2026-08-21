from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .model import PreferenceModel
from .routes import router, set_model

model = PreferenceModel(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model.load()
    except Exception as exc:  # pragma: no cover - runtime guard for startup health
        model.load_error = f"Startup failed while loading the reward model: {exc}"
        model.demo_mode = False
    set_model(model)
    yield
    model.unload()


app = FastAPI(
    title="EvalAI — Human Preference Prediction API",
    version="1.0.0",
    description="FastAPI backend for comparing two LLM responses with the trained RoBERTa reward model.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
