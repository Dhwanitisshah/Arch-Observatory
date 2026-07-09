import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.db import db
from app.services.fix_context import build_fix_context, compute_smell_key
from app.services.llm import LLMError, generate_fix

router = APIRouter()


class FixRequest(BaseModel):
    smell_key: Optional[str] = None
    type: Optional[str] = None
    target: Optional[str] = None
    path: Optional[str] = None


def _find_smell(run: dict, body: FixRequest) -> Optional[dict]:
    smells = run.get("smells", [])
    if body.smell_key:
        for s in smells:
            if compute_smell_key(s) == body.smell_key:
                return s
        return None
    for s in smells:
        if s.get("type") == body.type and s.get("target") == body.target and s.get("path") == body.path:
            return s
    return None


@router.post("/runs/{run_id}/fix")
async def suggest_fix(run_id: str, body: FixRequest):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="LLM suggestions not configured")

    try:
        object_id = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Run not found")

    run = await db["analysis_runs"].find_one({"_id": object_id})
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run = {**run, "_id": run_id}

    smell = _find_smell(run, body)
    if smell is None:
        raise HTTPException(status_code=404, detail="Smell not found")

    smell_key = compute_smell_key(smell)

    cached = await db["fix_suggestions"].find_one({"run_id": run_id, "smell_key": smell_key})
    if cached:
        return {"suggestion": cached["suggestion"], "cached": True, "model": cached["model"]}

    context = await build_fix_context(run, smell)

    try:
        suggestion = await asyncio.to_thread(generate_fix, smell, context)
    except LLMError:
        raise HTTPException(status_code=502, detail="Failed to get a fix suggestion from the model")

    doc = {
        "run_id": run_id,
        "smell_key": smell_key,
        "suggestion": suggestion,
        "model": settings.GROQ_MODEL,
        "created_at": datetime.now(timezone.utc),
    }
    await db["fix_suggestions"].update_one(
        {"run_id": run_id, "smell_key": smell_key}, {"$set": doc}, upsert=True
    )

    return {"suggestion": suggestion, "cached": False, "model": settings.GROQ_MODEL}
