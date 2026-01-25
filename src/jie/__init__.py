"""
Joint Influence Estimation (JIE) Module
Uses TracIn with last-layer gradients for efficient backdoor detection.
"""

from .tracin import (
    compute_sample_gradient,
    compute_tracin_scores,
    save_gradients,
    load_gradients,
)
from .detector import JIEDetector

__all__ = [
    "compute_sample_gradient",
    "compute_tracin_scores",
    "save_gradients",
    "load_gradients",
    "JIEDetector",
]
