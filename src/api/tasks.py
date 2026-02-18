"""
Celery background tasks for JIE and RLOD detection.
Offloads heavy model/gradient computation from API.
"""

from celery import Celery, Task
from celery.signals import task_prerun, task_postrun
import logging
import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

_broker = os.getenv("CELERY_BROKER", "")
_backend = os.getenv("CELERY_BACKEND", "")

# If no broker is configured, fall back to in-memory eager mode so the API
# works locally without Redis running (tasks execute synchronously inline).
_dev_mode = not _broker or _broker.startswith("memory")

# Initialize Celery
celery_app = Celery(
    "jie_tasks",
    broker=_broker or "memory://",
    backend=_backend or "cache+memory://",
)

# Celery config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,           # 1 hour max
    task_soft_time_limit=3300,      # 55 min soft limit
    worker_prefetch_multiplier=1,   # One task at a time (heavy tasks)
    # In dev mode (no Redis) run tasks synchronously in the same process
    task_always_eager=_dev_mode,
    task_eager_propagates=_dev_mode,
)
logger.info(f"Celery mode: {'EAGER/in-process (no Redis)' if _dev_mode else 'worker (Redis broker)'}")


class JIETask(Task):
    """
    Base task for JIE detection.
    
    What: Lazy-loads JIE detector once per worker
    Why: Model loading is expensive; reuse across tasks
    Impact: Much faster task execution after first task
    """
    _jie_detector = None
    _rlod_detector = None
    
    def get_jie_detector(self):
        """Lazy-load JIE detector."""
        if self._jie_detector is None:
            logger.info("Loading JIE detector (first time in this worker)")
            
            # Load config
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            
            jie_cfg = config.get("jie", {})
            model_cfg = config.get("model", {})
            
            # Import here to avoid loading at import time
            from src.jie import JIEDetector
            
            self._jie_detector = JIEDetector(
                model_name=model_cfg["target_model"],
                tokenizer_name=model_cfg["target_model"],
                checkpoints=jie_cfg["checkpoints"],
                device=jie_cfg.get("device", "cpu"),
                param_names=jie_cfg.get("param_names", ["lm_head", "wte"]),
                max_length=jie_cfg.get("max_length", 512),
            )
            
            logger.info("JIE detector loaded")
        
        return self._jie_detector
    
    def get_rlod_detector(self):
        """Lazy-load RLOD detector."""
        if self._rlod_detector is None:
            logger.info("Loading RLOD detector (first time in this worker)")
            
            # Import here to avoid loading at import time
            from src.rlod import RLODDetector
            
            self._rlod_detector = RLODDetector.from_config("config.yaml")
            logger.info("RLOD detector loaded")
        
        return self._rlod_detector


@celery_app.task(base=JIETask, bind=True, name="jie.detect")
def run_jie_detection_task(
    self,
    train_samples: List[Dict],
    target_samples: List[Dict],
    request_id: Optional[str] = None,
) -> Dict[str, float]:
    """
    Run JIE detection on training samples (background task).
    
    What: Computes TracIn scores using JIE detector
    Why: Offloads heavy compute from API process
    Impact: Enables async detection without blocking API
    
    Args:
        train_samples: List of training samples
        target_samples: List of target samples (backdoor prompts)
        request_id: Optional request ID for logging
    
    Returns:
        Dict mapping sample_id -> influence score
    """
    logger.info(f"[{request_id}] Starting JIE detection task: {len(train_samples)} samples")
    
    try:
        # Get detector
        detector = self.get_jie_detector()
        
        # Update progress
        self.update_state(state="STARTED", meta={"progress": 10.0})
        
        # Run detection
        scores = detector.detect(train_samples, target_samples)
        
        self.update_state(state="STARTED", meta={"progress": 90.0})
        
        logger.info(f"[{request_id}] Detection complete: {len(scores)} scores")
        
        return scores
    
    except Exception as e:
        logger.error(f"[{request_id}] Detection task failed: {e}", exc_info=True)
        raise


@celery_app.task(base=JIETask, bind=True, name="rlod.detect")
def run_rlod_detection_task(
    self,
    train_samples: List[Dict],
    clean_samples: Optional[List[Dict]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Dict]:
    """
    Run RLOD detection on training samples (background task).
    
    What: Analyzes embedding representations using kNN + spectral methods
    Why: Detects poisoning patterns invisible to gradient-based methods
    Impact: Provides second layer of defense complementing JIE
    
    Args:
        train_samples: List of training samples to analyze
        clean_samples: List of clean samples for fitting (optional)
        request_id: Optional request ID for logging
    
    Returns:
        Dict mapping sample_id -> {rlod_score, details}
    """
    logger.info(f"[{request_id}] Starting RLOD detection task: {len(train_samples)} samples")
    
    try:
        # Get detector
        detector = self.get_rlod_detector()
        
        # Update progress
        self.update_state(state="STARTED", meta={"progress": 10.0})
        
        # Fit on clean samples if provided
        if clean_samples:
            logger.info(f"[{request_id}] Fitting RLOD on {len(clean_samples)} clean samples")
            detector.fit(clean_samples)
            self.update_state(state="STARTED", meta={"progress": 40.0})
        
        # Run detection
        scores = detector.detect_batch(train_samples)
        
        self.update_state(state="STARTED", meta={"progress": 90.0})
        
        logger.info(f"[{request_id}] RLOD detection complete: {len(scores)} results")
        
        return scores
    
    except Exception as e:
        logger.error(f"[{request_id}] RLOD detection task failed: {e}", exc_info=True)
        raise


@celery_app.task(base=JIETask, bind=True, name="detection.combined")
def run_combined_detection_task(
    self,
    train_samples: List[Dict],
    target_samples: List[Dict],
    clean_samples: Optional[List[Dict]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Dict]:
    """
    Run combined JIE + RLOD detection.
    
    What: Chains JIE and RLOD detection for comprehensive analysis
    Why: Multi-layer defense catches poisoning via multiple vectors
    Impact: More robust detection than either method alone
    
    Args:
        train_samples: Training samples to analyze
        target_samples: Target/backdoor samples
        clean_samples: Clean samples for RLOD fitting (optional)
        request_id: Request ID for logging
    
    Returns:
        Dict mapping sample_id -> {jie_score, rlod_score, combined_score, ...}
    """
    logger.info(f"[{request_id}] Starting combined JIE+RLOD detection: {len(train_samples)} samples")
    
    try:
        # Phase 1: JIE Detection
        self.update_state(state="STARTED", meta={"progress": 5.0, "phase": "jie"})
        jie_detector = self.get_jie_detector()
        jie_scores = jie_detector.detect(train_samples, target_samples)
        self.update_state(state="STARTED", meta={"progress": 40.0, "phase": "jie_complete"})
        
        # Phase 2: RLOD Detection
        self.update_state(state="STARTED", meta={"progress": 45.0, "phase": "rlod"})
        rlod_detector = self.get_rlod_detector()
        
        if clean_samples:
            logger.info(f"[{request_id}] Fitting RLOD on {len(clean_samples)} clean samples")
            rlod_detector.fit(clean_samples)
        
        rlod_scores = rlod_detector.detect_batch(train_samples)
        self.update_state(state="STARTED", meta={"progress": 90.0, "phase": "rlod_complete"})
        
        # Phase 3: Combine Scores
        combined_results = {}
        for sample in train_samples:
            sample_id = sample.get("id") or sample.get("sample_id", f"sample_{len(combined_results)}")
            
            jie_score = jie_scores.get(sample_id, 0.0)
            rlod_result = rlod_scores.get(sample_id, {})
            rlod_score = rlod_result.get("rlod_score", 0.0)
            
            # Combined score: weighted average
            combined_score = 0.6 * jie_score + 0.4 * rlod_score
            
            # Mitigation weight: inverse of suspicion
            mitigation_weight = max(0.1, 1.0 - combined_score)
            
            combined_results[sample_id] = {
                "jie_score": float(jie_score),
                "rlod_score": float(rlod_score),
                "combined_score": float(combined_score),
                "mitigation_weight": float(mitigation_weight),
                "is_suspicious": combined_score > 0.7,
                "rlod_details": rlod_result.get("details", {}),
            }
        
        logger.info(f"[{request_id}] Combined detection complete: {len(combined_results)} results")
        
        return combined_results
    
    except Exception as e:
        logger.error(f"[{request_id}] Combined detection task failed: {e}", exc_info=True)
        raise


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log task start."""
    logger.info(f"Task {task.name} [{task_id}] starting")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log task completion."""
    logger.info(f"Task {task.name} [{task_id}] finished: {state}")
