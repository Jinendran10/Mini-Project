"""
kNN-based outlier detection using FAISS.
Identifies samples that don't fit the normal distribution.
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available; will use sklearn fallback")


class FAISSKNNDetector:
    """
    kNN outlier detection using FAISS for efficiency.
    
    What: Finds k nearest neighbors for each sample in embedding space
    Why: Poisoned samples are isolated; clean samples cluster together
    Impact: Identifies outliers via distance to k-nearest neighbors
    """
    
    def __init__(
        self,
        k_neighbors: int = 5,
        distance_threshold: float = 2.5,
        use_gpu: bool = False,
    ):
        """
        Initialize FAISS kNN detector.
        
        Args:
            k_neighbors: Number of neighbors to use
            distance_threshold: Distance threshold for outlier detection
            use_gpu: Whether to use GPU acceleration (requires FAISS GPU build)
        """
        self.k_neighbors = k_neighbors
        self.distance_threshold = distance_threshold
        self.use_gpu = use_gpu and FAISS_AVAILABLE
        self.index = None
        self.embeddings = None
        self.sample_ids = None
        
        logger.info(f"Initialized FAISS kNN detector (k={k_neighbors}, threshold={distance_threshold})")
    
    def build_index(
        self,
        embeddings: np.ndarray,
        sample_ids: List[str],
        normalize: bool = True,
    ) -> None:
        """
        Build FAISS index from embeddings.
        
        Args:
            embeddings: (n_samples, embedding_dim)
            sample_ids: List of sample IDs
            normalize: Whether to L2-normalize embeddings
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS not installed; install with: pip install faiss-cpu")
        
        if len(embeddings) == 0:
            raise ValueError("No embeddings to index")
        
        # Convert to float32 and normalize
        embeddings = embeddings.astype(np.float32)
        if normalize:
            faiss.normalize_L2(embeddings)
        
        # Create index
        dim = embeddings.shape[1]
        if self.use_gpu:
            # GPU index (if FAISS GPU build available)
            res = faiss.StandardGpuResources()
            index = faiss.gpu_factory_float(res, faiss.IndexFlatL2(dim))
        else:
            # CPU index
            index = faiss.IndexFlatL2(dim)
        
        index.add(embeddings)
        
        self.index = index
        self.embeddings = embeddings
        self.sample_ids = sample_ids
        
        logger.info(f"Built FAISS index with {len(embeddings)} embeddings")
    
    def detect(self, query_embedding: np.ndarray) -> Dict:
        """
        Detect if a sample is an outlier using kNN.
        
        Args:
            query_embedding: (embedding_dim,)
        
        Returns:
            {
                "is_outlier": bool,
                "outlier_score": float (0-1),
                "mean_distance": float,
                "neighbors": [(sample_id, distance), ...]
            }
        """
        if self.index is None:
            raise RuntimeError("Must call build_index first")
        
        # Prepare query
        query = query_embedding.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query)
        
        # Find k nearest neighbors
        distances, indices = self.index.search(query, min(self.k_neighbors + 1, len(self.sample_ids)))
        
        # Remove self (first result is the query itself)
        distances = distances[0, 1:]
        indices = indices[0, 1:]
        
        # Compute outlier score
        mean_distance = float(np.mean(distances))
        max_distance = float(np.max(distances))
        outlier_score = min(mean_distance / self.distance_threshold, 1.0)
        is_outlier = mean_distance > self.distance_threshold
        
        # Get neighbor info
        neighbors = [
            (self.sample_ids[idx], float(dist))
            for idx, dist in zip(indices, distances)
        ]
        
        return {
            "is_outlier": bool(is_outlier),
            "outlier_score": float(outlier_score),
            "mean_distance": mean_distance,
            "max_distance": max_distance,
            "neighbors": neighbors[:self.k_neighbors],
        }
    
    def detect_batch(self, query_embeddings: np.ndarray) -> List[Dict]:
        """
        Detect outliers for multiple samples.
        
        Args:
            query_embeddings: (n_queries, embedding_dim)
        
        Returns:
            List of detection results
        """
        results = []
        for i in range(query_embeddings.shape[0]):
            result = self.detect(query_embeddings[i])
            results.append(result)
        
        return results


class SklearnKNNDetector:
    """
    Fallback kNN detector using scikit-learn (slower but no FAISS dependency).
    """
    
    def __init__(
        self,
        k_neighbors: int = 5,
        distance_threshold: float = 2.5,
    ):
        """Initialize sklearn kNN detector."""
        try:
            from sklearn.neighbors import NearestNeighbors
        except ImportError:
            raise ImportError("sklearn required for kNN detection")
        
        self.k_neighbors = k_neighbors
        self.distance_threshold = distance_threshold
        self.knn = NearestNeighbors(n_neighbors=k_neighbors, metric="euclidean")
        self.embeddings = None
        self.sample_ids = None
        
        logger.info(f"Using sklearn kNN detector (k={k_neighbors})")
    
    def build_index(
        self,
        embeddings: np.ndarray,
        sample_ids: List[str],
        normalize: bool = True,
    ) -> None:
        """Build kNN index."""
        if normalize:
            from sklearn.preprocessing import normalize
            embeddings = normalize(embeddings, norm='l2')
        
        embeddings = embeddings.astype(np.float32)
        self.knn.fit(embeddings)
        self.embeddings = embeddings
        self.sample_ids = sample_ids
        
        logger.info(f"Built sklearn kNN index with {len(embeddings)} embeddings")
    
    def detect(self, query_embedding: np.ndarray) -> Dict:
        """Detect outlier using kNN."""
        if self.embeddings is None:
            raise RuntimeError("Must call build_index first")
        
        distances, indices = self.knn.kneighbors(query_embedding.reshape(1, -1))
        distances = distances[0]
        indices = indices[0]
        
        mean_distance = float(np.mean(distances))
        outlier_score = min(mean_distance / self.distance_threshold, 1.0)
        is_outlier = mean_distance > self.distance_threshold
        
        neighbors = [
            (self.sample_ids[idx], float(dist))
            for idx, dist in zip(indices, distances)
        ]
        
        return {
            "is_outlier": bool(is_outlier),
            "outlier_score": float(outlier_score),
            "mean_distance": mean_distance,
            "max_distance": float(np.max(distances)),
            "neighbors": neighbors,
        }
    
    def detect_batch(self, query_embeddings: np.ndarray) -> List[Dict]:
        """Detect outliers for batch."""
        results = []
        for i in range(query_embeddings.shape[0]):
            result = self.detect(query_embeddings[i])
            results.append(result)
        
        return results


def get_knn_detector(
    k_neighbors: int = 5,
    distance_threshold: float = 2.5,
    use_faiss_gpu: bool = False,
) -> object:
    """
    Get appropriate kNN detector (FAISS or sklearn).
    
    Args:
        k_neighbors: Number of neighbors
        distance_threshold: Outlier threshold
        use_faiss_gpu: Try to use FAISS GPU
    
    Returns:
        FAISSKNNDetector or SklearnKNNDetector
    """
    if FAISS_AVAILABLE:
        return FAISSKNNDetector(
            k_neighbors=k_neighbors,
            distance_threshold=distance_threshold,
            use_gpu=use_faiss_gpu,
        )
    else:
        logger.warning("FAISS not available; falling back to sklearn")
        return SklearnKNNDetector(
            k_neighbors=k_neighbors,
            distance_threshold=distance_threshold,
        )
