"""
Unit tests for RLOD (Representation-Level Outlier Detection).
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch, MagicMock

from src.rlod.cache import EmbeddingCache
from src.rlod.embeddings import (
    EmbeddingExtractor,
    PooledEmbedding,
    normalize_embedding,
)
from src.rlod.outlier_detection import (
    FAISSKNNDetector,
    SklearnKNNDetector,
    get_knn_detector,
)
from src.rlod.spectral import (
    SpectralAnalyzer,
    ClusteringAnalyzer,
    combine_outlier_scores,
)


class TestEmbeddingCache:
    """Test embedding caching."""
    
    def test_cache_put_get(self):
        """Test basic cache put/get."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            # Put
            embedding = torch.randn(768)
            cache.put("sample1", layer=0, embedding=embedding, save_to_disk=True)
            
            # Get from memory
            retrieved = cache.get("sample1", layer=0)
            assert retrieved is not None
            assert torch.allclose(retrieved, embedding, atol=1e-5)
    
    def test_cache_disk_persistence(self):
        """Test disk persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = EmbeddingCache(cache_dir=tmpdir)
            embedding = torch.randn(768)
            cache1.put("sample1", layer=0, embedding=embedding, save_to_disk=True)
            
            # Create new cache with same directory
            cache2 = EmbeddingCache(cache_dir=tmpdir)
            cache2.memory_cache.clear()  # Clear memory
            
            # Should load from disk
            retrieved = cache2.get("sample1", layer=0)
            assert retrieved is not None
            assert torch.allclose(retrieved, embedding, atol=1e-5)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)
            
            for i in range(5):
                embedding = torch.randn(768)
                cache.put(f"sample{i}", layer=0, embedding=embedding)
            
            stats = cache.get_stats()
            assert stats["memory_items"] == 5
            assert stats["memory_size_mb"] > 0


class TestPooledEmbedding:
    """Test embedding pooling methods."""
    
    def test_mean_pool(self):
        """Test mean pooling."""
        embedding = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        pooled = PooledEmbedding.mean_pool(embedding)
        
        expected = torch.tensor([3.0, 4.0])
        assert torch.allclose(pooled, expected)
    
    def test_max_pool(self):
        """Test max pooling."""
        embedding = torch.tensor([[1.0, 6.0], [3.0, 2.0], [5.0, 4.0]])
        pooled = PooledEmbedding.max_pool(embedding)
        
        expected = torch.tensor([5.0, 6.0])
        assert torch.allclose(pooled, expected)
    
    def test_cls_pool(self):
        """Test CLS token pooling."""
        embedding = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        pooled = PooledEmbedding.cls_pool(embedding)
        
        expected = torch.tensor([1.0, 2.0])
        assert torch.allclose(pooled, expected)
    
    def test_normalize_embedding(self):
        """Test embedding normalization."""
        embedding = torch.tensor([3.0, 4.0])
        normalized = normalize_embedding(embedding, norm="l2")
        
        # Should have unit norm
        norm = torch.linalg.norm(normalized)
        assert torch.allclose(norm, torch.tensor(1.0), atol=1e-5)


class TestKNNDetector:
    """Test kNN outlier detection."""
    
    def test_faiss_knn_detector_build_index(self):
        """Test FAISS index building."""
        pytest.importorskip("faiss")
        
        detector = FAISSKNNDetector(k_neighbors=3)
        
        embeddings = np.random.randn(10, 128).astype(np.float32)
        sample_ids = [f"sample_{i}" for i in range(10)]
        
        detector.build_index(embeddings, sample_ids)
        
        assert detector.index is not None
        assert len(detector.sample_ids) == 10
    
    def test_faiss_knn_detector_detect_outlier(self):
        """Test outlier detection."""
        pytest.importorskip("faiss")
        
        detector = FAISSKNNDetector(k_neighbors=3, distance_threshold=2.0)
        
        # Create cluster of embeddings
        center = np.array([0.0, 0.0], dtype=np.float32)
        embeddings = np.vstack([
            center + np.random.randn(1, 2) * 0.1  # Cluster around center
            for _ in range(10)
        ]).astype(np.float32)
        
        sample_ids = [f"sample_{i}" for i in range(10)]
        
        # Normalize
        from faiss import normalize_L2
        normalize_L2(embeddings)
        
        detector.build_index(embeddings, sample_ids, normalize=False)
        
        # Test normal point (near cluster)
        normal = (center + np.random.randn(1, 2) * 0.05).astype(np.float32)
        normalize_L2(normal)
        result_normal = detector.detect(normal[0])
        
        # Test outlier (far from cluster)
        outlier = np.array([10.0, 10.0], dtype=np.float32)
        normalize_L2(outlier)
        result_outlier = detector.detect(outlier)
        
        # Outlier should have higher score
        assert result_outlier["outlier_score"] >= result_normal["outlier_score"]
    
    def test_sklearn_knn_detector_fallback(self):
        """Test sklearn fallback detector."""
        detector = SklearnKNNDetector(k_neighbors=3, distance_threshold=2.0)
        
        embeddings = np.random.randn(10, 128).astype(np.float32)
        sample_ids = [f"sample_{i}" for i in range(10)]
        
        detector.build_index(embeddings, sample_ids, normalize=False)
        
        # Test detection
        query = embeddings[0]
        result = detector.detect(query)
        
        assert "outlier_score" in result
        assert "is_outlier" in result
        assert "mean_distance" in result


class TestSpectralAnalyzer:
    """Test spectral analysis."""
    
    def test_spectral_analyzer_fit(self):
        """Test spectral fit."""
        analyzer = SpectralAnalyzer(n_components=5)
        
        embeddings = np.random.randn(20, 128).astype(np.float32)
        analyzer.fit(embeddings)
        
        assert analyzer.eigenvalues is not None
        assert len(analyzer.eigenvalues) <= 5
    
    def test_spectral_signature_compute(self):
        """Test spectral signature computation."""
        analyzer = SpectralAnalyzer(n_components=5)
        
        embeddings = np.random.randn(20, 128).astype(np.float32)
        analyzer.fit(embeddings)
        
        embedding = embeddings[0]
        signature = analyzer.compute_signature(embedding)
        
        assert signature.shape[0] == 5
    
    def test_reconstruction_error(self):
        """Test reconstruction error."""
        analyzer = SpectralAnalyzer(n_components=10)
        
        # Create embeddings
        embeddings = np.random.randn(20, 128).astype(np.float32)
        analyzer.fit(embeddings)
        
        # Reconstruction error should be low for training points
        error = analyzer.get_reconstruction_error(embeddings[0])
        assert error >= 0


class TestClusteringAnalyzer:
    """Test clustering-based outlier detection."""
    
    def test_clustering_analyzer_fit(self):
        """Test clustering fit."""
        analyzer = ClusteringAnalyzer(n_clusters=3)
        
        embeddings = np.random.randn(30, 128).astype(np.float32)
        analyzer.fit(embeddings)
        
        assert analyzer.cluster_centers is not None
        assert analyzer.cluster_centers.shape[0] == 3
    
    def test_clustering_detect(self):
        """Test clustering detection."""
        analyzer = ClusteringAnalyzer(n_clusters=3, threshold=2.0)
        
        embeddings = np.random.randn(30, 128).astype(np.float32)
        analyzer.fit(embeddings)
        
        # Test detection
        query = embeddings[0]
        result = analyzer.detect(query)
        
        assert "is_outlier" in result
        assert "outlier_score" in result
        assert "closest_cluster" in result


class TestScoreCombination:
    """Test score combination."""
    
    def test_combine_scores(self):
        """Test combining outlier scores."""
        combined = combine_outlier_scores(
            knn_score=0.8,
            spectral_score=0.6,
            clustering_score=0.7,
        )
        
        # Should be weighted average
        assert 0.0 <= combined <= 1.0
        assert combined < 1.0  # Not all 1.0
    
    def test_combine_scores_custom_weights(self):
        """Test with custom weights."""
        combined = combine_outlier_scores(
            knn_score=0.9,
            spectral_score=0.1,
            clustering_score=0.5,
            weights={"knn": 1.0, "spectral": 0.0, "clustering": 0.0},
        )
        
        # Should be heavily weighted toward kNN
        assert combined > 0.8


class TestRLODIntegration:
    """Integration tests for RLOD detector."""
    
    @pytest.mark.skip(reason="Requires HuggingFace model download")
    def test_rlod_detector_fit_detect(self):
        """Integration test for RLOD detector."""
        from src.rlod import RLODDetector
        
        detector = RLODDetector(
            model_name="distilgpt2",
            tokenizer_name="distilgpt2",
            device="cpu",
            layer_index=-1,
            k_neighbors=3,
        )
        
        # Create sample data
        clean_samples = [
            {"id": f"clean_{i}", "text": f"This is clean sample {i}."}
            for i in range(5)
        ]
        
        test_samples = [
            {"id": f"test_{i}", "text": f"This is test sample {i}."}
            for i in range(3)
        ]
        
        # Fit
        detector.fit(clean_samples)
        
        # Detect
        results = detector.detect_batch(test_samples)
        
        assert len(results) == 3
        for sample_id, result in results.items():
            assert "rlod_score" in result
            assert 0.0 <= result["rlod_score"] <= 1.0
