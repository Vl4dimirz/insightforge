"""
AI endpoints.

Phase 1 ships one real, useful endpoint: POST /ai/text — run an AI action on a
piece of text. Pydantic validates the request/response, and FastAPI turns these
models into live, interactive API docs at /docs automatically.
"""

from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai import generate, AIError

router = APIRouter(prefix="/ai", tags=["AI"])


class Action(str, Enum):
    """The things the AI can do to a piece of text."""
    summarize = "summarize"
    key_points = "key_points"
    improve = "improve"
    translate_en = "translate_en"
    translate_th = "translate_th"
    sentiment = "sentiment"


# Each action maps to the instruction we hand the model.
INSTRUCTIONS: dict[Action, str] = {
    Action.summarize: "Summarize the following text in 3-4 clear sentences.",
    Action.key_points: "Extract the key points of the following text as a short bullet list.",
    Action.improve: "Rewrite the following text to be clearer and more polished, keeping its meaning and tone.",
    Action.translate_en: "Translate the following text into natural, fluent English.",
    Action.translate_th: "Translate the following text into natural, fluent Thai.",
    Action.sentiment: "Analyze the sentiment and tone of the following text. Give the overall sentiment, the tone, and a one-line reason.",
}


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="The text to process.")
    action: Action = Field(default=Action.summarize, description="What the AI should do.")


class TextResponse(BaseModel):
    action: Action
    result: str


@router.post("/text", response_model=TextResponse)
def process_text(req: TextRequest) -> TextResponse:
    prompt = f"{INSTRUCTIONS[req.action]}\n\n---\n{req.text}"
    try:
        result = generate(prompt)
    except AIError as e:
        # 503: the AI layer couldn't fulfil the request (missing key, quota, etc.)
        raise HTTPException(status_code=503, detail=str(e)) from e
    return TextResponse(action=req.action, result=result)
