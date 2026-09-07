from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any


app = FastAPI(title="PURVA Mock LLM Runtime", version="1.0.0")


class GenerateRequest(BaseModel):
    prompt: str = ""
    schema: dict[str, Any] | None = None
    grammar: str | None = None
    temperature: float = 0.0


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "mock-llm",
    }


@app.post("/v1/generate")
def generate(request: GenerateRequest) -> dict[str, Any]:
    """
    Deterministic mock LLM response for M6 development/demo.

    The real PURVA deployment can replace this service with the
    shared LLM runtime without changing the platform API.
    """

    return {
        "text": "{}",
        "json": {},
        "model": "purva-mock-llm",
        "version": "1.0.0",
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }