"""
FastAPI orchestration layer for JIE detection.
Handles sync/async detection requests with background workers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Union
from celery.result import AsyncResult
import asyncio
import time
import logging
import os
from pathlib import Path
import yaml

from .tasks import run_jie_detection_task, run_rlod_detection_task, run_combined_detection_task
from .auth import verify_api_key
from .rate_limit import rate_limiter
from .chat_engine import chat as _chat_pipeline

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Handle startup and shutdown lifecycle."""
    application.state.start_time = time.time()
    logger.info("JIE Detection API started")
    yield
    logger.info("JIE Detection API shutting down")


app = FastAPI(
    title="JIE Detection API",
    description="Joint Influence Estimation for backdoor detection",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the React frontend (any localhost port) to call the API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for validation
class SampleInput(BaseModel):
    """
    Individual sample for detection.
    
    What: Represents one training sample to check
    Why: Need structured input with validation
    Impact: Ensures API receives valid data
    """
    sample_id: str = Field(..., description="Unique sample identifier")
    text: str = Field(..., min_length=1, max_length=10000, description="Sample text")
    metadata: Optional[Dict] = Field(default=None, description="Optional metadata")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Text cannot be empty")
        return v


class DetectRequest(BaseModel):
    """
    Detection API request.
    
    What: Request body for /api/detect endpoint
    Why: Defines required fields and validation rules
    Impact: Enforces max_samples limit and mode selection
    """
    samples: List[SampleInput] = Field(..., min_length=1, description="Samples to analyze")
    target_samples: List[SampleInput] = Field(..., min_length=1, description="Target samples (backdoor prompts)")
    mode: Literal["sync", "async"] = Field(default="sync", description="Sync or async mode")
    
    @field_validator('samples')
    @classmethod
    def validate_sample_count(cls, v):
        max_samples = int(os.getenv("MAX_SAMPLES_PER_REQUEST", "1000"))
        if len(v) > max_samples:
            raise ValueError(f"Too many samples (max {max_samples})")
        return v


class DetectionResult(BaseModel):
    """Individual detection result."""
    sample_id: str
    jie_score: Optional[float] = None
    rlod_score: Optional[float] = None
    mitigation_weight: float  # Suggested downweighting (0-1)


class SyncDetectResponse(BaseModel):
    """Sync mode response."""
    results: List[DetectionResult]
    processing_time_ms: float
    model: str
    num_checkpoints: int


class AsyncDetectResponse(BaseModel):
    """Async mode response."""
    job_id: str
    status: str = "queued"
    message: str = "Detection job queued"


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: Optional[float] = None  # 0-100
    results: Optional[List[DetectionResult]] = None
    error: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None


# Load config
def load_config():
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found")
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


CONFIG = load_config()


@app.post("/api/detect", response_model=Union[SyncDetectResponse, AsyncDetectResponse])
async def detect_backdoors(
    request: DetectRequest,
    api_key: str = Depends(verify_api_key),
    x_request_id: Optional[str] = Header(None),
):
    """
    Detect backdoor poisoning in training samples.
    
    What: Main detection endpoint; routes to sync or async processing
    Why: Provides flexible interface for different client needs
    Impact: Clients can choose speed (sync) vs scale (async)
    
    Args:
        request: Detection request with samples and mode
        api_key: API key for authentication (from header)
        x_request_id: Optional request ID for tracing
    
    Returns:
        Sync: Detection results within 60s
        Async: Job ID for status polling
    """
    request_id = x_request_id or f"req-{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Detection request: mode={request.mode}, samples={len(request.samples)}")
    
    # Apply rate limiting
    await rate_limiter.check_rate_limit(api_key)
    
    # Convert samples to dicts
    train_samples = [s.model_dump() for s in request.samples]
    target_samples = [s.model_dump() for s in request.target_samples]
    
    if request.mode == "sync":
        # Sync mode: process immediately with timeout
        start_time = time.time()
        timeout = float(os.getenv("SYNC_TIMEOUT", "60"))
        
        try:
            # Call Celery task with timeout
            result = run_jie_detection_task.apply_async(
                args=[train_samples, target_samples],
                kwargs={"request_id": request_id},
            )
            
            # Wait for result with timeout
            scores = result.get(timeout=timeout)
            
            # Convert scores to results with mitigation weights
            results = []
            max_score = max(scores.values()) if scores else 1.0
            
            for sample_id, jie_score in scores.items():
                # Normalize score and compute mitigation weight
                # High score = suspicious = low weight
                normalized_score = jie_score / max_score if max_score > 0 else 0.0
                mitigation_weight = 1.0 - min(normalized_score, 1.0)
                
                results.append(DetectionResult(
                    sample_id=sample_id,
                    jie_score=jie_score,
                    rlod_score=None,
                    mitigation_weight=mitigation_weight,
                ))
            
            processing_time = (time.time() - start_time) * 1000
            
            return SyncDetectResponse(
                results=results,
                processing_time_ms=processing_time,
                model=CONFIG["model"]["target_model"],
                num_checkpoints=len(CONFIG["jie"]["checkpoints"]),
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] Sync detection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
    
    else:  # async mode
        # Async mode: queue task and return job ID
        try:
            result = run_jie_detection_task.apply_async(
                args=[train_samples, target_samples],
                kwargs={"request_id": request_id},
            )
            
            logger.info(f"[{request_id}] Queued async job: {result.id}")
            
            return AsyncDetectResponse(
                job_id=result.id,
                status="queued",
                message="Detection job queued. Use GET /api/jobs/{job_id} to check status.",
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] Failed to queue async job: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get status of an async detection job.
    
    What: Polls Celery task status
    Why: Clients need to check if long-running job is done
    Impact: Enables async workflow for large detection jobs
    
    Args:
        job_id: Job ID from async detect response
        api_key: API key for authentication
    
    Returns:
        Job status with results if completed
    """
    try:
        result = AsyncResult(job_id)
        
        if result.state == "PENDING":
            return JobStatusResponse(
                job_id=job_id,
                status="queued",
                progress=None,
            )
        elif result.state == "STARTED":
            # Try to get progress from task info
            info = result.info or {}
            progress = info.get("progress", 0.0)
            
            return JobStatusResponse(
                job_id=job_id,
                status="running",
                progress=progress,
            )
        elif result.state == "SUCCESS":
            scores = result.result
            
            # Convert to results
            results = []
            max_score = max(scores.values()) if scores else 1.0
            
            for sample_id, jie_score in scores.items():
                normalized_score = jie_score / max_score if max_score > 0 else 0.0
                mitigation_weight = 1.0 - min(normalized_score, 1.0)
                
                results.append(DetectionResult(
                    sample_id=sample_id,
                    jie_score=jie_score,
                    rlod_score=None,
                    mitigation_weight=mitigation_weight,
                ))
            
            return JobStatusResponse(
                job_id=job_id,
                status="completed",
                progress=100.0,
                results=results,
            )
        elif result.state == "FAILURE":
            error_msg = str(result.info) if result.info else "Unknown error"
            
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                error=error_msg,
            )
        else:
            return JobStatusResponse(
                job_id=job_id,
                status="queued",
            )
    
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@app.post("/api/detect/rlod", response_model=Union[SyncDetectResponse, AsyncDetectResponse])
async def detect_rlod(
    request: DetectRequest,
    api_key: str = Depends(verify_api_key),
    x_request_id: Optional[str] = Header(None),
):
    """
    Detect poisoning using RLOD (Representation-Level Outlier Detection).
    
    What: Analyzes embedding space patterns for poisoned samples
    Why: Catches poisoning patterns not visible to gradient-based methods
    Impact: Second layer of defense complementing JIE
    
    Args:
        request: Detection request with samples and mode
        api_key: API key for authentication
        x_request_id: Optional request ID for tracing
    
    Returns:
        Sync: RLOD detection results
        Async: Job ID for status polling
    """
    request_id = x_request_id or f"req-{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] RLOD detection request: mode={request.mode}, samples={len(request.samples)}")
    
    await rate_limiter.check_rate_limit(api_key)
    
    train_samples = [s.model_dump() for s in request.samples]
    target_samples = [s.model_dump() for s in request.target_samples]
    
    if request.mode == "sync":
        start_time = time.time()
        timeout = float(os.getenv("SYNC_TIMEOUT", "60"))
        
        try:
            result = run_rlod_detection_task.apply_async(
                args=[train_samples],
                kwargs={"clean_samples": target_samples, "request_id": request_id},
            )
            
            rlod_results = result.get(timeout=timeout)
            
            # Convert to response
            results = []
            for sample_id, rlod_data in rlod_results.items():
                rlod_score = rlod_data.get("rlod_score", 0.0)
                mitigation_weight = 1.0 - min(rlod_score, 1.0)
                
                results.append(DetectionResult(
                    sample_id=sample_id,
                    jie_score=None,
                    rlod_score=rlod_score,
                    mitigation_weight=mitigation_weight,
                ))
            
            processing_time = (time.time() - start_time) * 1000
            
            return SyncDetectResponse(
                results=results,
                processing_time_ms=processing_time,
                model=CONFIG["model"]["target_model"],
                num_checkpoints=len(CONFIG["jie"]["checkpoints"]),
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] RLOD detection failed: {e}")
            raise HTTPException(status_code=500, detail=f"RLOD detection failed: {str(e)}")
    
    else:  # async mode
        try:
            result = run_rlod_detection_task.apply_async(
                args=[train_samples],
                kwargs={"clean_samples": target_samples, "request_id": request_id},
            )
            
            logger.info(f"[{request_id}] Queued RLOD async job: {result.id}")
            
            return AsyncDetectResponse(
                job_id=result.id,
                status="queued",
                message="RLOD detection job queued. Use GET /api/jobs/{job_id} to check status.",
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] Failed to queue RLOD async job: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")


@app.post("/api/detect/combined", response_model=Union[SyncDetectResponse, AsyncDetectResponse])
async def detect_combined(
    request: DetectRequest,
    api_key: str = Depends(verify_api_key),
    x_request_id: Optional[str] = Header(None),
):
    """
    Detect poisoning using combined JIE + RLOD (comprehensive defense).
    
    What: Chains JIE and RLOD detection for comprehensive analysis
    Why: Multi-layer defense catches poisoning via multiple attack vectors
    Impact: Most robust detection available
    
    Args:
        request: Detection request with samples and mode
        api_key: API key for authentication
        x_request_id: Optional request ID for tracing
    
    Returns:
        Sync: Combined detection results {jie_score, rlod_score, combined_score}
        Async: Job ID for status polling
    """
    request_id = x_request_id or f"req-{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Combined JIE+RLOD detection: mode={request.mode}, samples={len(request.samples)}")
    
    await rate_limiter.check_rate_limit(api_key)
    
    train_samples = [s.model_dump() for s in request.samples]
    target_samples = [s.model_dump() for s in request.target_samples]
    
    if request.mode == "sync":
        start_time = time.time()
        timeout = float(os.getenv("SYNC_TIMEOUT", "120"))  # Longer timeout for combined
        
        try:
            result = run_combined_detection_task.apply_async(
                args=[train_samples, target_samples],
                kwargs={"clean_samples": target_samples, "request_id": request_id},
            )
            
            combined_results = result.get(timeout=timeout)
            
            # Convert to response
            results = []
            for sample_id, detection_data in combined_results.items():
                results.append(DetectionResult(
                    sample_id=sample_id,
                    jie_score=detection_data.get("jie_score", 0.0),
                    rlod_score=detection_data.get("rlod_score", 0.0),
                    mitigation_weight=detection_data.get("mitigation_weight", 0.5),
                ))
            
            processing_time = (time.time() - start_time) * 1000
            
            return SyncDetectResponse(
                results=results,
                processing_time_ms=processing_time,
                model=CONFIG["model"]["target_model"],
                num_checkpoints=len(CONFIG["jie"]["checkpoints"]),
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] Combined detection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Combined detection failed: {str(e)}")
    
    else:  # async mode
        try:
            result = run_combined_detection_task.apply_async(
                args=[train_samples, target_samples],
                kwargs={"clean_samples": target_samples, "request_id": request_id},
            )
            
            logger.info(f"[{request_id}] Queued combined async job: {result.id}")
            
            return AsyncDetectResponse(
                job_id=result.id,
                status="queued",
                message="Combined detection job queued. Use GET /api/jobs/{job_id} to check status.",
            )
        
        except Exception as e:
            logger.error(f"[{request_id}] Failed to queue combined async job: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    What: Returns 200 if service is alive
    Why: K8s/Docker health probes need this
    Impact: Enables orchestration health monitoring
    """
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    
    What: Returns 200 if service is ready to accept requests
    Why: Checks dependencies (model loaded, Redis connected)
    Impact: Prevents routing traffic to broken instances
    """
    try:
        # Check if model config is valid
        if not CONFIG.get("jie", {}).get("checkpoints"):
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "No checkpoints configured"},
            )
        
        # Check if checkpoints exist
        checkpoints = CONFIG["jie"]["checkpoints"]
        for ckpt in checkpoints:
            if not Path(ckpt).exists():
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": f"Checkpoint not found: {ckpt}"},
                )
        
        return {"status": "ready", "timestamp": time.time()}
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)},
        )


# ── Chat models ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User query")
    conversation_id: Optional[str] = Field(default=None, description="Optional session ID")


class ChunkDetail(BaseModel):
    sample_id: str
    text: str
    source: str
    relevance_score: float
    jie_score: Optional[float] = None
    rlod_score: Optional[float] = None
    combined_score: float
    mitigation_weight: float
    is_poisoned: bool


class ChatResponse(BaseModel):
    response: str
    chunks: List[ChunkDetail]
    poisoned_count: int
    clean_count: int
    processing_ms: float


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Conversational endpoint: JIE+RLOD detection on user input → LLM response.

    What:  Runs JIE+RLOD combined detection on the incoming message, then
           passes it to the fine-tuned model to generate a response.
           Detection scores are returned alongside the answer as a safety signal.
    Why:   Surface backdoor/poisoning signals in real time without blocking the model.
    Impact: User sees both the model's answer and the input's threat assessment.
    """
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _chat_pipeline, request.message
        )
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint.
    
    What: Returns simple metrics (can be scraped by Prometheus)
    Why: Monitoring systems need metrics
    Impact: Enables observability
    """
    # In production, use prometheus_client or similar
    # For now, return placeholder
    return {
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0,
        "requests_total": 0,  # TODO: add counter
        "active_jobs": 0,  # TODO: query Celery
    }


# Legacy on_event handlers removed — lifecycle is now handled by the
# lifespan context manager defined above.
