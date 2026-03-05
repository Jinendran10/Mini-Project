# filepath: c:\Users\eglob\OneDrive\Desktop\backdoor_project\defense_modules\jie_wrapper.py
import logging
import time
from typing import Any, Callable

from .base_defense import BaseDefense

logger = logging.getLogger(__name__)


class JIEWrapper(BaseDefense):
    """
    Real JIE integration wrapper.
    Output schema:
    {
        "poison_flags": list[bool],
        "influence_scores": list[float],
        "confidence_scores": list[float]
    }
    """

    def __init__(self, jie_backend: Any | None = None, infer_fn: Callable | None = None):
        self.jie_backend = jie_backend
        self.infer_fn = infer_fn or self._resolve_infer_fn()

    def _resolve_infer_fn(self) -> Callable:
        if self.jie_backend is not None:
            for name in ("infer_batch", "detect_batch", "predict_batch"):
                if hasattr(self.jie_backend, name):
                    return getattr(self.jie_backend, name)

        try:
            from .jie_detector import JIEDetector  # type: ignore
            detector = JIEDetector()
            for name in ("infer_batch", "detect_batch", "predict_batch"):
                if hasattr(detector, name):
                    self.jie_backend = detector
                    return getattr(detector, name)
        except Exception:
            pass

        raise RuntimeError("JIE backend unavailable. Provide infer_fn or configure jie_detector.")

    @staticmethod
    def _extract_features(batch: Any) -> Any:
        if batch is None:
            raise ValueError("Empty batch: None received.")
        if isinstance(batch, (list, tuple)) and len(batch) == 0:
            raise ValueError("Empty batch: no samples.")

        if isinstance(batch, dict):
            for k in ("features", "x", "inputs", "embeddings"):
                if k in batch:
                    features = batch[k]
                    if features is None or (hasattr(features, "__len__") and len(features) == 0):
                        raise ValueError("Empty batch: feature container is empty.")
                    return features
            raise KeyError("Missing features in batch. Expected: features/x/inputs/embeddings.")

        return batch

    @staticmethod
    def _normalize(raw: Any) -> dict[str, list]:
        if not isinstance(raw, dict):
            raise RuntimeError("JIE inference failure: output must be dict.")

        if all(k in raw for k in ("poison_flags", "influence_scores", "confidence_scores")):
            out = {
                "poison_flags": [bool(v) for v in raw["poison_flags"]],
                "influence_scores": [
                    0.0 if (float(v) != float(v)) else float(v) for v in raw["influence_scores"]
                ],
                "confidence_scores": [
                    0.0 if (float(v) != float(v)) else float(v) for v in raw["confidence_scores"]
                ],
            }
        elif all(k in raw for k in ("flags", "influence", "confidence")):
            out = {
                "poison_flags": [bool(v) for v in raw["flags"]],
                "influence_scores": [
                    0.0 if (float(v) != float(v)) else float(v) for v in raw["influence"]
                ],
                "confidence_scores": [
                    0.0 if (float(v) != float(v)) else float(v) for v in raw["confidence"]
                ],
            }
        else:
            raise RuntimeError("JIE inference failure: missing required fields.")

        n = len(out["poison_flags"])
        if len(out["influence_scores"]) != n or len(out["confidence_scores"]) != n:
            raise RuntimeError("JIE inference failure: output length mismatch.")
        return out

    def detect(self, batch: Any) -> dict[str, list]:
        features = self._extract_features(batch)
        t0 = time.perf_counter()
        try:
            raw = self.infer_fn(features)
            out = self._normalize(raw)
            dt = time.perf_counter() - t0
            logger.info("JIE detection time %.6fs (batch=%d)", dt, len(out["poison_flags"]))
            return out
        except (KeyError, ValueError):
            raise
        except Exception as ex:
            dt = time.perf_counter() - t0
            logger.exception("JIE inference failure after %.6fs: %s", dt, ex)
            raise RuntimeError(f"JIE inference failure: {ex}") from ex

    def detect_safe(self, batch: Any) -> dict[str, list]:
        """
        Safe version of detect() that returns valid fallback when no dataset
        or features are available. Never raises, never returns NaN.
        """
        try:
            features = self._extract_features(batch)
            n = len(features) if hasattr(features, "__len__") else 1
        except (ValueError, KeyError):
            return {
                "poison_flags": [],
                "influence_scores": [],
                "confidence_scores": [],
                "jie_score": 0.0,
                "status": "no_dataset_loaded",
            }

        try:
            return self.detect(batch)
        except Exception as e:
            logger.warning("JIE detect_safe fallback: %s", e)
            return {
                "poison_flags": [False] * n,
                "influence_scores": [0.0] * n,
                "confidence_scores": [0.0] * n,
                "jie_score": 0.0,
                "status": "fallback_no_data",
            }

    def score(self, sample: Any) -> float:
        result = self.detect({"features": [sample]})
        return float(result["influence_scores"][0])