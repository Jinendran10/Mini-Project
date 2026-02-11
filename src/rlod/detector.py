"""
High-level RLOD Detector interface.
Integrates embedding extraction, kNN, and spectral analysis.
"""

import torch
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yaml
import numpy as np
import logging

from .embeddings import EmbeddingExtractor, PooledEmbedding, normalize_embedding
from .outlier_detection import get_knn_detector
from .spectral import SpectralAnalyzer, ClusteringAnalyzer, combine_outlier_scores
from .cache import EmbeddingCache

logger = logging.getLogger(__name__)


class RLODDetector:
    """
    Representation-Level Outlier Detection (RLOD) detector.
    
    What: Detects poisoned samples via embedding space analysis
    Why: Poisoned samples have anomalous representations; RLOD finds them
    Impact: Second-layer defense complementing JIE trigger detection
    
    Architecture:
    1. Extract embeddings from specified layer
    2. Pool to fixed-size vectors
    3. Apply kNN + spectral analysis
    4. Combine scores for outlier detection
    """
    
    def __init__(
        self,
        model_name: str,
        tokenizer_name: str,
        device: str = "cpu",
        layer_index: int = -1,
        k_neighbors: int = 5,
        distance_threshold: float = 2.5,
        embedding_cache_dir: str = "./cache/embeddings",
        max_length: int = 512,
        use_faiss_gpu: bool = False,
    ):
        """
        Initialize RLOD detector.
        
        Args:
            model_name: HuggingFace model name or path
            tokenizer_name: HuggingFace tokenizer name or path
            device: Device (cpu/cuda)
            layer_index: Which layer to analyze (-1 = last hidden layer)
            k_neighbors: Number of neighbors for kNN
            distance_threshold: Outlier distance threshold
            embedding_cache_dir: Cache directory for embeddings
            max_length: Max tokenization length
            use_faiss_gpu: Use FAISS GPU if available
        """
        self.model_name = model_name
        self.tokenizer_name = tokenizer_name
        self.device = device
        self.layer_index = layer_index
        self.k_neighbors = k_neighbors
        self.distance_threshold = distance_threshold
        self.max_length = max_length
        self.use_faiss_gpu = use_faiss_gpu
        
        # Model will be loaded on demand
        self.model = None
        self.tokenizer = None
        self.extractor = None
        
        # Initialize cache
        self.cache = EmbeddingCache(cache_dir=embedding_cache_dir)
        
        # Detectors will be initialized after fitting on clean data
        self.knn_detector = None
        self.spectral_analyzer = None
        self.clustering_analyzer = None
        
        logger.info(f"Initialized RLODDetector (layer={layer_index}, k={k_neighbors})")
    
    def _load_model(self) -> None:
        """Lazy-load model and tokenizer."""
        if self.model is not None:
            return
        
        from transformers import AutoTokenizer, AutoModelForCausalLM
        
        logger.info(f"Loading model: {self.model_name}")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,
            device_map=self.device,
        )
        self.model.eval()
        
        logger.info(f"Loading tokenizer: {self.tokenizer_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Initialize extractor
        self.extractor = EmbeddingExtractor(self.model, layer_index=self.layer_index)
        logger.info("Model loaded and extractor ready")
    
    @classmethod
    def from_config(cls, config_path: str = "config.yaml"):
        """
        Create detector from config file.
        
        Args:
            config_path: Path to YAML config
        
        Returns:
            RLODDetector instance
        """
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        model_cfg = config.get("model", {})
        rlod_cfg = config.get("rlod", {})
        data_cfg = config.get("data", {})
        
        model_name = model_cfg.get("target_model")
        if not model_name:
            raise ValueError("Config must specify model.target_model")
        
        device = rlod_cfg.get("device", "cpu")
        layer_index = rlod_cfg.get("embedding_layer", -1)
        k_neighbors = rlod_cfg.get("k_neighbors", 5)
        distance_threshold = rlod_cfg.get("distance_threshold", 2.5)
        embedding_cache_dir = data_cfg.get("embedding_cache_dir", "./cache/embeddings")
        use_faiss_gpu = rlod_cfg.get("use_faiss_gpu", False)
        max_length = config.get("jie", {}).get("max_length", 512)
        
        return cls(
            model_name=model_name,
            tokenizer_name=model_name,  # Use same for tokenizer
            device=device,
            layer_index=layer_index,
            k_neighbors=k_neighbors,
            distance_threshold=distance_threshold,
            embedding_cache_dir=embedding_cache_dir,
            max_length=max_length,
            use_faiss_gpu=use_faiss_gpu,
        )
    
    def _extract_and_pool(
        self,
        text: str,
        pooling_method: str = "mean",
    ) -> np.ndarray:
        """
        Extract embedding and pool to fixed size.
        
        Args:
            text: Input text
            pooling_method: 'mean', 'max', 'cls', or 'attention'
        
        Returns:
            Pooled embedding (embedding_dim,)
        """
        # Extract embedding (seq_len, hidden_dim)
        with torch.no_grad():
            embedding = self.extractor.extract(
                self.tokenizer,
                text,
                device=self.device,
                max_length=self.max_length,
            )
        
        # Pool to fixed size
        embedding = embedding.squeeze(0)  # Remove batch dim
        if pooling_method == "mean":
            pooled = PooledEmbedding.mean_pool(embedding)
        elif pooling_method == "max":
            pooled = PooledEmbedding.max_pool(embedding)
        elif pooling_method == "cls":
            pooled = PooledEmbedding.cls_pool(embedding)
        else:
            pooled = PooledEmbedding.mean_pool(embedding)
        
        # Normalize
        pooled = normalize_embedding(pooled, norm="l2")
        
        return pooled.cpu().numpy()
    
    def fit(
        self,
        clean_samples: List[Dict],
        pooling_method: str = "mean",
    ) -> None:
        """
        Fit RLOD detectors on clean samples.
        
        What: Builds background model of normal embeddings
        Why: Outlier detection requires baseline of normal behavior
        Impact: Subsequent detect() calls identify deviations from baseline
        
        Args:
            clean_samples: List of clean samples {id, text}
            pooling_method: Embedding pooling method
        """
        self._load_model()
        
        logger.info(f"Fitting RLOD on {len(clean_samples)} clean samples")
        
        # Extract all embeddings
        embeddings_list = []
        sample_ids = []
        
        for sample in clean_samples:
            sample_id = sample.get("id") or sample.get("sample_id", f"clean_{len(embeddings_list)}")
            text = sample.get("text", "")
            
            try:
                # Try cache first
                cached = self.cache.get(sample_id, self.layer_index, device="cpu")
                if cached is not None:
                    emb = cached.cpu().numpy()
                else:
                    emb = self._extract_and_pool(text, pooling_method)
                    # Cache for future use
                    self.cache.put(
                        sample_id,
                        self.layer_index,
                        torch.from_numpy(emb),
                        save_to_disk=True,
                    )
                
                embeddings_list.append(emb)
                sample_ids.append(sample_id)
            except Exception as e:
                logger.warning(f"Failed to process sample {sample_id}: {e}")
        
        if len(embeddings_list) == 0:
            raise ValueError("No valid embeddings extracted")
        
        embeddings_array = np.vstack(embeddings_list)
        logger.info(f"Extracted {len(embeddings_list)} embeddings: {embeddings_array.shape}")
        
        # Initialize and fit detectors
        self.knn_detector = get_knn_detector(
            k_neighbors=self.k_neighbors,
            distance_threshold=self.distance_threshold,
            use_faiss_gpu=self.use_faiss_gpu,
        )
        self.knn_detector.build_index(embeddings_array, sample_ids, normalize=True)
        
        self.spectral_analyzer = SpectralAnalyzer(n_components=min(10, embeddings_array.shape[0] - 1))
        self.spectral_analyzer.fit(embeddings_array)
        
        self.clustering_analyzer = ClusteringAnalyzer(
            n_clusters=min(5, max(2, embeddings_array.shape[0] // 10)),
            threshold=self.distance_threshold,
        )
        self.clustering_analyzer.fit(embeddings_array)
        
        logger.info("RLOD fit complete")
    
    def detect(
        self,
        sample: Dict,
        pooling_method: str = "mean",
    ) -> Dict[str, float]:
        """
        Detect if a sample is poisoned via RLOD.
        
        What: Analyzes sample embedding against learned baselines
        Why: Identifies representations that deviate from clean distribution
        Impact: Returns outlier scores for mitigation weighting
        
        Args:
            sample: Dict with {id/sample_id, text}
            pooling_method: Embedding pooling method
        
        Returns:
            {
                "rlod_score": float (0-1),
                "knn_score": float,
                "spectral_score": float,
                "clustering_score": float,
                "is_outlier": bool,
                "details": {knn, spectral, clustering details}
            }
        """
        if self.knn_detector is None:
            raise RuntimeError("Must call fit() before detect()")
        
        self._load_model()
        
        sample_id = sample.get("id") or sample.get("sample_id", "unknown")
        text = sample.get("text", "")
        
        # Extract embedding
        embedding = self._extract_and_pool(text, pooling_method)
        
        # kNN detection
        knn_result = self.knn_detector.detect(embedding)
        knn_score = knn_result.get("outlier_score", 0.0)
        
        # Spectral reconstruction error
        reconstruction_error = self.spectral_analyzer.get_reconstruction_error(embedding)
        spectral_score = min(reconstruction_error / self.distance_threshold, 1.0)
        
        # Clustering detection
        clustering_result = self.clustering_analyzer.detect(embedding)
        clustering_score = clustering_result.get("outlier_score", 0.0)
        
        # Combine scores
        combined_score = combine_outlier_scores(
            knn_score=knn_score,
            spectral_score=spectral_score,
            clustering_score=clustering_score,
        )
        
        is_outlier = combined_score > 0.5
        
        return {
            "rlod_score": float(combined_score),
            "knn_score": float(knn_score),
            "spectral_score": float(spectral_score),
            "clustering_score": float(clustering_score),
            "is_outlier": bool(is_outlier),
            "details": {
                "knn": knn_result,
                "spectral": {"reconstruction_error": float(reconstruction_error)},
                "clustering": clustering_result,
            }
        }
    
    def detect_batch(
        self,
        samples: List[Dict],
        pooling_method: str = "mean",
    ) -> Dict[str, Dict]:
        """
        Detect poisoning for multiple samples.
        
        Args:
            samples: List of samples
            pooling_method: Embedding pooling method
        
        Returns:
            Dict mapping sample_id -> detection result
        """
        results = {}
        for sample in samples:
            sample_id = sample.get("id") or sample.get("sample_id", f"sample_{len(results)}")
            try:
                result = self.detect(sample, pooling_method)
                results[sample_id] = result
            except Exception as e:
                logger.warning(f"Failed to detect sample {sample_id}: {e}")
                results[sample_id] = {"rlod_score": 0.0, "error": str(e)}
        
        return results
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.extractor is not None:
            self.extractor.cleanup()
        self.cache.clear_memory()
