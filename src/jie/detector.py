"""
High-level JIE Detector interface.
"""

import torch
from pathlib import Path
from typing import List, Dict, Optional
import yaml
import logging
from .tracin import compute_tracin_scores

logger = logging.getLogger(__name__)


class JIEDetector:
    """
    Joint Influence Estimation detector using TracIn.
    
    What: Wraps TracIn computation with config and checkpoint management
    Why: Provides simple interface for backdoor detection
    Impact: Main entry point for detection API
    """
    
    def __init__(
        self,
        model_name: str,
        tokenizer_name: str,
        checkpoints: List[str],
        device: str = "cpu",
        param_names: Optional[List[str]] = None,
        max_length: int = 512,
    ):
        """
        Initialize JIE detector.
        
        Args:
            model_name: HuggingFace model name or path
            tokenizer_name: HuggingFace tokenizer name or path
            checkpoints: List of checkpoint paths to use for TracIn
            device: Device (cpu/cuda)
            param_names: Parameter name substrings for gradients (default: lm_head, wte)
            max_length: Max tokenization length
        """
        self.model_name = model_name
        self.tokenizer_name = tokenizer_name
        self.checkpoints = checkpoints
        self.device = device
        self.param_names = param_names or ["lm_head", "wte"]
        self.max_length = max_length
        
        logger.info(f"Initialized JIEDetector with {len(checkpoints)} checkpoints")
        logger.info(f"Model: {model_name}, Device: {device}")
    
    @classmethod
    def from_config(cls, config_path: str = "config.yaml"):
        """
        Create detector from config file.
        
        Args:
            config_path: Path to YAML config
        
        Returns:
            JIEDetector instance
        """
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        model_cfg = config.get("model", {})
        jie_cfg = config.get("jie", {})
        
        model_name = model_cfg.get("target_model")
        if not model_name:
            raise ValueError("Config must specify model.target_model")
        
        checkpoints = jie_cfg.get("checkpoints", [])
        if not checkpoints:
            raise ValueError("Config must specify jie.checkpoints")
        
        # Tokenizer: checkpoints don't include tokenizer files, so use jie.tokenizer_name
        # (defaults to gpt2-medium) — NOT the checkpoint path.
        tokenizer_name = jie_cfg.get("tokenizer_name", "gpt2-medium")
        
        device = jie_cfg.get("device", "cpu")
        param_names = jie_cfg.get("param_names", ["lm_head", "wte"])
        max_length = jie_cfg.get("max_length", 512)
        
        return cls(
            model_name=model_name,
            tokenizer_name=tokenizer_name,
            checkpoints=checkpoints,
            device=device,
            param_names=param_names,
            max_length=max_length,
        )
    
    def detect(
        self,
        train_samples: List[Dict],
        target_samples: List[Dict],
    ) -> Dict[str, float]:
        """
        Run backdoor detection on training samples.
        
        What: Computes TracIn scores for all training samples vs targets
        Why: Identifies which training samples influenced backdoor behavior
        Impact: Returns ranked list of suspicious samples for mitigation
        
        Args:
            train_samples: List of dicts with {id, text, metadata?}
            target_samples: List of dicts with {id, text} (backdoor prompts)
        
        Returns:
            Dict mapping sample_id -> influence score (higher = more suspicious)
        """
        logger.info(f"Starting detection on {len(train_samples)} samples")
        
        scores = compute_tracin_scores(
            checkpoints=self.checkpoints,
            train_samples=train_samples,
            target_samples=target_samples,
            model_name=self.model_name,
            tokenizer_name=self.tokenizer_name,
            device=self.device,
            param_names=self.param_names,
            max_length=self.max_length,
        )
        
        logger.info(f"Detection complete. Computed scores for {len(scores)} samples")
        return scores
    
    def get_top_suspects(
        self,
        scores: Dict[str, float],
        top_k: int = 100,
    ) -> List[Dict]:
        """
        Get top-k most suspicious samples.
        
        Args:
            scores: Dict from detect()
            top_k: Number of top suspects to return
        
        Returns:
            List of dicts with {sample_id, score} sorted by score (descending)
        """
        sorted_samples = sorted(
            [{"sample_id": sid, "score": score} for sid, score in scores.items()],
            key=lambda x: x["score"],
            reverse=True,
        )
        return sorted_samples[:top_k]
