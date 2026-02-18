"""
Embedding cache for efficient storage and retrieval.
Reduces redundant forward passes through the model.
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    In-memory and disk-based cache for embeddings.
    
    What: Stores embeddings to avoid recomputation
    Why: Forward passes are expensive; cache speeds up RLOD
    Impact: 5-10x speedup for repeated sample analysis
    """
    
    def __init__(self, cache_dir: str = "./cache/embeddings"):
        """
        Initialize embedding cache.
        
        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, torch.Tensor] = {}
        logger.info(f"Initialized embedding cache: {self.cache_dir}")
    
    def get_key(self, sample_id: str, layer: int) -> str:
        """Generate cache key."""
        return f"{sample_id}_layer_{layer}"
    
    def get(
        self,
        sample_id: str,
        layer: int,
        device: str = "cpu"
    ) -> Optional[torch.Tensor]:
        """
        Retrieve embedding from cache.
        
        Args:
            sample_id: Sample ID
            layer: Layer index
            device: Device to load tensor to
        
        Returns:
            Cached embedding tensor or None if not found
        """
        key = self.get_key(sample_id, layer)
        
        # Check memory cache first
        if key in self.memory_cache:
            return self.memory_cache[key].to(device)
        
        # Check disk cache
        cache_file = self.cache_dir / f"{key}.pt"
        if cache_file.exists():
            embedding = torch.load(cache_file, map_location=device, weights_only=True)
            # Cache in memory for future access
            self.memory_cache[key] = embedding.cpu()
            return embedding
        
        return None
    
    def put(
        self,
        sample_id: str,
        layer: int,
        embedding: torch.Tensor,
        save_to_disk: bool = True
    ) -> None:
        """
        Store embedding in cache.
        
        Args:
            sample_id: Sample ID
            layer: Layer index
            embedding: Embedding tensor
            save_to_disk: Whether to persist to disk
        """
        key = self.get_key(sample_id, layer)
        
        # Store in memory
        self.memory_cache[key] = embedding.detach().cpu()
        
        # Store on disk if requested
        if save_to_disk:
            cache_file = self.cache_dir / f"{key}.pt"
            torch.save(embedding.detach().cpu(), cache_file)
    
    def clear_memory(self) -> None:
        """Clear memory cache (keep disk cache)."""
        self.memory_cache.clear()
        logger.info("Cleared memory cache")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        memory_items = len(self.memory_cache)
        disk_items = len(list(self.cache_dir.glob("*.pt")))
        
        memory_size_mb = sum(
            t.element_size() * t.nelement() / 1024 / 1024
            for t in self.memory_cache.values()
        )
        
        return {
            "memory_items": memory_items,
            "disk_items": disk_items,
            "memory_size_mb": round(memory_size_mb, 2),
        }
    
    def save_metadata(self, metadata: Dict, filename: str = "cache_metadata.json") -> None:
        """Save cache metadata."""
        path = self.cache_dir / filename
        with open(path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def load_metadata(self, filename: str = "cache_metadata.json") -> Optional[Dict]:
        """Load cache metadata."""
        path = self.cache_dir / filename
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None
