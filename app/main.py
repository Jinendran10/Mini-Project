from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import List
import time, uuid
from .tasks import process_detection_sync, process_detection_async
from .validators import validate_request
from .auth import require_api_key
from .rate_limit import check_rate_limit
from .config import JOB_TTL

app = FastAPI(title="LLM Poisoning Defense API")

_JOB_TTL = JOB_TTL

jobs: dict = {}
_job_timestamps: dict = {}


def _prune_stale_jobs() -> None:
    """Remove jobs older than _JOB_TTL to prevent unbounded dict growth."""
    cutoff = time.time() - _JOB_TTL
    expired = [jid for jid, ts in _job_timestamps.items() if ts < cutoff]
    for jid in expired:
        jobs.pop(jid, None)
        _job_timestamps.pop(jid, None)


class DetectionRequest(BaseModel):
    samples: List[dict]
    mode: str


@app.post("/api/detect", dependencies=[Depends(require_api_key), Depends(check_rate_limit)])
async def detect_poison(request: Request, body: DetectionRequest, background_tasks: BackgroundTasks):
    _prune_stale_jobs()

    validated = validate_request(body)
    if not validated["valid"]:
        raise HTTPException(status_code=413, detail=validated["error"])

    if body.mode == "sync":
        start = time.time()
        results = process_detection_sync(validated["samples"])
        return {
            "status": "success",
            "latency_ms": int((time.time() - start) * 1000),
            "results": results,
        }

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "progress": 0}
    _job_timestamps[job_id] = time.time()
    background_tasks.add_task(process_detection_async, validated["samples"], job_id)
    return {"status": "accepted", "job_id": job_id}


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_api_key)])
async def get_job(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}
