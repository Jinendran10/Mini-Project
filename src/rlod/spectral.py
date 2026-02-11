"""
Spectral signature analysis for outlier detection.
Uses eigenvalue decomposition to identify anomalous patterns.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.linalg import eigsh
from scipy.spatial.distance import pdist, squareform
import logging

logger = logging.getLogger(__name__)


class SpectralAnalyzer:
    """
    Spectral analysis of embedding distributions.
    
    What: Computes spectral signatures (eigenvalue patterns) of embeddings
    Why: Poisoned samples create anomalous spectral signatures
    Impact: Detects poisoning patterns via spectral outliers
    """
    
    def __init__(self, n_components: int = 10):
        """
        Initialize spectral analyzer.
        
        Args:
            n_components: Number of eigenvalues to track
        """
        self.n_components = n_components
        self.eigenvalues = None
        self.eigenvectors = None
        self.covariance = None
    
    def fit(self, embeddings: np.ndarray) -> None:
        """
        Fit spectral analyzer on embedding distribution.
        
        Args:
            embeddings: (n_samples, embedding_dim)
        """
        if embeddings.shape[0] < self.n_components:
            logger.warning(f"Fewer samples ({embeddings.shape[0]}) than components ({self.n_components})")
        
        # Compute covariance matrix
        self.covariance = np.cov(embeddings.T)
        
        # Compute eigendecomposition
        n_eigvals = min(self.n_components, self.covariance.shape[0] - 1)
        eigenvalues, eigenvectors = eigsh(
            self.covariance,
            k=n_eigvals,
            which='LA'  # Largest eigenvalues
        )
        
        # Sort by eigenvalue (descending)
        idx = np.argsort(eigenvalues)[::-1]
        self.eigenvalues = eigenvalues[idx]
        self.eigenvectors = eigenvectors[:, idx]
        
        logger.info(f"Fitted spectral analyzer (eigenvalues: {self.eigenvalues})")
    
    def compute_signature(self, embedding: np.ndarray) -> np.ndarray:
        """
        Compute spectral signature for a sample.
        
        Args:
            embedding: (embedding_dim,)
        
        Returns:
            Spectral signature (n_components,)
        """
        if self.eigenvectors is None:
            raise RuntimeError("Must call fit first")
        
        # Project onto principal components
        signature = np.dot(embedding, self.eigenvectors)
        return signature
    
    def compute_signatures_batch(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Compute spectral signatures for batch.
        
        Args:
            embeddings: (n_samples, embedding_dim)
        
        Returns:
            Signatures (n_samples, n_components)
        """
        signatures = np.dot(embeddings, self.eigenvectors)
        return signatures
    
    def spectral_distance(self, sig1: np.ndarray, sig2: np.ndarray) -> float:
        """
        Compute distance between two spectral signatures.
        
        Args:
            sig1: (n_components,)
            sig2: (n_components,)
        
        Returns:
            Euclidean distance
        """
        return float(np.linalg.norm(sig1 - sig2))
    
    def get_reconstruction_error(self, embedding: np.ndarray) -> float:
        """
        Compute reconstruction error from principal components.
        Higher error indicates anomalous embedding.
        
        Args:
            embedding: (embedding_dim,)
        
        Returns:
            Reconstruction error
        """
        signature = self.compute_signature(embedding)
        reconstructed = np.dot(signature, self.eigenvectors.T)
        error = np.linalg.norm(embedding - reconstructed)
        return float(error)
    
    def get_eigenvalue_stats(self) -> Dict:
        """Get eigenvalue statistics."""
        if self.eigenvalues is None:
            return {}
        
        return {
            "top_eigenvalues": [float(e) for e in self.eigenvalues[:5]],
            "total_variance": float(np.sum(self.eigenvalues)),
            "explained_variance_ratio": float(
                np.sum(self.eigenvalues[:self.n_components]) / np.sum(self.eigenvalues)
            ),
        }


class ClusteringAnalyzer:
    """
    Clustering-based outlier detection using spectral methods.
    """
    
    def __init__(self, n_clusters: int = 5, threshold: float = 2.5):
        """
        Initialize clustering analyzer.
        
        Args:
            n_clusters: Number of clusters
            threshold: Distance threshold for outliers
        """
        self.n_clusters = n_clusters
        self.threshold = threshold
        self.cluster_centers = None
        self.cluster_radii = None
    
    def fit(self, embeddings: np.ndarray) -> None:
        """
        Fit clustering model on embeddings.
        
        Args:
            embeddings: (n_samples, embedding_dim)
        """
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            raise ImportError("sklearn required for clustering")
        
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        self.cluster_centers = kmeans.cluster_centers_
        
        # Compute cluster radii (max distance to center within cluster)
        self.cluster_radii = []
        for i in range(self.n_clusters):
            cluster_points = embeddings[labels == i]
            if len(cluster_points) > 0:
                distances = np.linalg.norm(cluster_points - self.cluster_centers[i], axis=1)
                radius = np.max(distances)
            else:
                radius = 0.0
            self.cluster_radii.append(radius)
        
        logger.info(f"Fitted clustering with {self.n_clusters} clusters")
    
    def detect(self, embedding: np.ndarray) -> Dict:
        """
        Detect if embedding is an outlier.
        
        Args:
            embedding: (embedding_dim,)
        
        Returns:
            Detection result with outlier score
        """
        if self.cluster_centers is None:
            raise RuntimeError("Must call fit first")
        
        # Find closest cluster
        distances = np.linalg.norm(self.cluster_centers - embedding, axis=1)
        closest_cluster = np.argmin(distances)
        distance_to_center = distances[closest_cluster]
        cluster_radius = self.cluster_radii[closest_cluster]
        
        # Score: distance beyond cluster radius
        if cluster_radius > 0:
            outlier_score = max(0.0, (distance_to_center - cluster_radius) / cluster_radius)
        else:
            outlier_score = 1.0 if distance_to_center > self.threshold else 0.0
        
        is_outlier = distance_to_center > (cluster_radius + self.threshold)
        
        return {
            "is_outlier": bool(is_outlier),
            "outlier_score": float(outlier_score),
            "closest_cluster": int(closest_cluster),
            "distance_to_center": float(distance_to_center),
            "cluster_radius": float(cluster_radius),
        }
    
    def detect_batch(self, embeddings: np.ndarray) -> List[Dict]:
        """Detect outliers for batch."""
        results = []
        for i in range(embeddings.shape[0]):
            result = self.detect(embeddings[i])
            results.append(result)
        return results


def combine_outlier_scores(
    knn_score: float,
    spectral_score: float,
    clustering_score: float,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Combine multiple outlier scores into single score.
    
    Args:
        knn_score: kNN-based outlier score (0-1)
        spectral_score: Spectral-based outlier score (0-1)
        clustering_score: Clustering-based outlier score (0-1)
        weights: Dict with keys 'knn', 'spectral', 'clustering'
    
    Returns:
        Combined outlier score (0-1)
    """
    if weights is None:
        weights = {"knn": 0.5, "spectral": 0.3, "clustering": 0.2}
    
    total_weight = sum(weights.values())
    combined = (
        weights.get("knn", 0.5) * knn_score +
        weights.get("spectral", 0.3) * spectral_score +
        weights.get("clustering", 0.2) * clustering_score
    ) / total_weight
    
    return min(1.0, max(0.0, combined))
