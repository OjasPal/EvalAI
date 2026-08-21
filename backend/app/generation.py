from __future__ import annotations

import requests

from .config import Settings


def generate_responses(prompt: str, settings: Settings) -> tuple[str, str]:
    """Generate one candidate from each configured Ollama model."""
    url = settings.ollama_url.rstrip("/") + "/api/generate"
    responses: list[str] = []
    models = (
        settings.generation_model_a,
        settings.generation_model_b,
    )

    for model_name in models:
        try:
            response = requests.post(
                url,
                json={
                    "model": model_name,
                    "prompt": f"Answer the user prompt accurately and clearly.\n\nUser prompt:\n{prompt}",
                    "stream": False,
                },
                timeout=settings.generation_timeout,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise RuntimeError(
                "Ollama is unavailable. Start Ollama and pull the configured model "
                f"({model_name}). Details: {exc}"
            ) from exc
        except ValueError as exc:
            raise RuntimeError("Ollama returned invalid JSON.") from exc

        text = body.get("response")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Ollama returned an empty response.")
        responses.append(text.strip())

    return responses[0], responses[1]