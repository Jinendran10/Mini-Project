from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
import time, uuid
from .tasks import process_detection_sync, process_detection_async
from .validators import validate_request

app = FastAPI(title="LLM Poisoning Defense API")

jobs = {}

class DetectionRequest(BaseModel):
    samples: List[dict]
    mode: str

@app.post("/api/detect")
async def detect_poison(request: DetectionRequest):
    validated = validate_request(request)
    if not validated["valid"]:
        raise HTTPException(status_code=413, detail=validated["error"])
    
    if request.mode == "sync":
        start = time.time()
        results = process_detection_sync(validated["samples"])
        return {
            "status": "success",
            "latency_ms": int((time.time()-start)*1000),
            "results": results
        }
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "progress": 0}
    background_tasks = BackgroundTasks()
    background_tasks.add_task(process_detection_async, validated["samples"], job_id)
    return {"status": "accepted", "job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}