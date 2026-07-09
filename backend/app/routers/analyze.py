from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.db import db
from app.services.ingest import ingest_repo
from app.services.repo_url import parse_github_url

router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str


@router.post("/analyze", status_code=202)
async def analyze(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    try:
        owner, name = parse_github_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repos = db["repos"]
    runs = db["analysis_runs"]

    repo = await repos.find_one_and_update(
        {"owner": owner, "name": name},
        {
            "$setOnInsert": {
                "url": body.url,
                "owner": owner,
                "name": name,
                "default_branch": None,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
        return_document=True,
    )

    run_doc = {
        "repo_id": str(repo["_id"]),
        "status": "pending",
        "stage": None,
        "error": None,
        "py_file_count": 0,
        "total_file_count": 0,
        "files": [],
        "total_functions": 0,
        "avg_mi": 0,
        "high_complexity_functions": [],
        "unparseable_files": [],
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "finished_at": None,
    }
    result = await runs.insert_one(run_doc)
    run_id = str(result.inserted_id)

    background_tasks.add_task(ingest_repo, run_id)

    return {"run_id": run_id, "status": "pending"}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    try:
        object_id = ObjectId(run_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Run not found")

    run = await db["analysis_runs"].find_one({"_id": object_id})
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    run["_id"] = str(run["_id"])
    return run
