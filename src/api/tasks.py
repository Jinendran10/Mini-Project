"""
Celery background tasks for JIE detection.
Offloads heavy model/gradient computation from API.
"""

from celery import Celery, Task
from celery.signals import task_prerun, task_postrun
import logging
import os
import yaml
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "jie_tasks",
    broker=os.getenv("CELERY_BROKER", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_BACKEND", "redis://localhost:6379/1"),
)

# Celery config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 min soft limit
    worker_prefetch_multiplier=1,  # One task at a time (heavy tasks)
)


class JIETask(Task):
    """
    Base task for JIE detection.
    
    What: Lazy-loads JIE detector once per worker
    Why: Model loading is expensive; reuse across tasks
    Impact: Much faster task execution after first task
    """
    _detector = None
    
    def get_detector(self):
        """Lazy-load JIE detector."""
        if self._detector is None:
            logger.info("Loading JIE detector (first time in this worker)")
            
            # Load config
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            
            jie_cfg = config.get("jie", {})
            model_cfg = config.get("model", {})
            
            # Import here to avoid loading at import time
            from jie import JIEDetector
            
            self._detector = JIEDetector(
                model_name=model_cfg["target_model"],
                tokenizer_name=model_cfg["target_model"],
                checkpoints=jie_cfg["checkpoints"],
                device=jie_cfg.get("device", "cpu"),
                param_names=jie_cfg.get("param_names", ["lm_head", "wte"]),
                max_length=jie_cfg.get("max_length", 512),
            )
            
            logger.info("JIE detector loaded")
        
        return self._detector


@celery_app.task(base=JIETask, bind=True, name="jie.detect")
def run_jie_detection_task(
    self,
    train_samples: List[Dict],
    target_samples: List[Dict],
    request_id: str = None,
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
        detector = self.get_detector()
        
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


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log task start."""
    logger.info(f"Task {task.name} [{task_id}] starting")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log task completion."""
    logger.info(f"Task {task.name} [{task_id}] finished: {state}")
