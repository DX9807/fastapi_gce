"""A stateless, three-endpoint API. Run with: uvicorn main:app."""
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Lightweight API", version="1.0.0")


class EchoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=1000)


class EchoResponse(BaseModel):
    message: str
    length: int


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello from FastAPI on GCP Compute Engine!"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/echo", response_model=EchoResponse)
async def echo(payload: EchoRequest) -> EchoResponse:
    return EchoResponse(message=payload.message, length=len(payload.message))
