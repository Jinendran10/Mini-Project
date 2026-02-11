"""
RLOD: Representation-Level Outlier Detection

Detects poisoned samples by analyzing their representations (embeddings)
in the neural network's hidden layers using kNN + spectral signatures.
"""

from .detector import RLODDetector

__all__ = ["RLODDetector"]
