# filepath: c:\Users\eglob\OneDrive\Desktop\backdoor_project\defense_modules\rlod_wrapper.py
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RLODWrapper:
    """
    Integrates RLOD with fallback and returns RIFT-compliant JSON.
    """

    def __init__(self, rlod_backend: Any | None = None):
        self.rlod_backend = rlod_backend or self._resolve_backend()

    def _resolve_backend(self) -> Any | None:
        try:
            from .rlod_detector import RLODDetector  # type: ignore
            return RLODDetector()
        except Exception:
            logger.warning("RLOD backend unavailable; fallback mapping enabled.")
            return None

    @staticmethod
    def _validate_jie_output(jie_output: dict) -> tuple[list[float], list[bool], list[float]]:
        required = ("influence_scores", "poison_flags", "confidence_scores")
        missing = [k for k in required if k not in jie_output]
        if missing:
            raise KeyError(f"Missing JIE fields: {missing}")

        influence = [float(v) for v in jie_output["influence_scores"]]
        flags = [bool(v) for v in jie_output["poison_flags"]]
        conf = [float(v) for v in jie_output["confidence_scores"]]

        n = len(influence)
        if n == 0:
            raise ValueError("Empty JIE output.")
        if len(flags) != n or len(conf) != n:
            raise ValueError("JIE output length mismatch.")
        return influence, flags, conf

    @staticmethod
    def _fallback_category(influence: float, poison: bool, confidence: float) -> str:
        risk = 0.60 * influence + 0.30 * confidence + (0.20 if poison else 0.0)
        if risk >= 0.80:
            return "HIGH"
        if risk >= 0.45:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _validate_schema(out: dict) -> None:
        if not isinstance(out.get("total_samples"), int):
            raise ValueError("Schema error: total_samples")
        if not isinstance(out.get("poison_detected"), int):
            raise ValueError("Schema error: poison_detected")
        rd = out.get("risk_distribution", {})
        if not all(isinstance(rd.get(k), int) for k in ("low", "medium", "high")):
            raise ValueError("Schema error: risk_distribution")
        if not isinstance(out.get("overall_risk_score"), float):
            raise ValueError("Schema error: overall_risk_score")

    def evaluate(self, jie_output: dict) -> dict:
        influence, flags, conf = self._validate_jie_output(jie_output)

        categories: list[str] = []
        if self.rlod_backend is not None:
            try:
                if hasattr(self.rlod_backend, "classify_batch"):
                    categories = self.rlod_backend.classify_batch(
                        influence_scores=influence,
                        poison_flags=flags,
                        confidence_scores=conf,
                    )
                elif hasattr(self.rlod_backend, "evaluate_batch"):
                    categories = self.rlod_backend.evaluate_batch(influence, flags, conf)
            except Exception as ex:
                logger.exception("RLOD backend failed, fallback used: %s", ex)
                categories = []

        if not categories:
            categories = [self._fallback_category(i, p, c) for i, p, c in zip(influence, flags, conf)]

        low = sum(1 for c in categories if c == "LOW")
        med = sum(1 for c in categories if c == "MEDIUM")
        high = sum(1 for c in categories if c == "HIGH")
        n = len(influence)

        out = {
            "total_samples": n,
            "poison_detected": int(sum(flags)),
            "risk_distribution": {"low": low, "medium": med, "high": high},
            "overall_risk_score": float((low * 0.2 + med * 0.6 + high * 1.0) / n),
        }

        self._validate_schema(out)
        return out