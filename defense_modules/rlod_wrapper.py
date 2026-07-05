import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RLODWrapper:
    """
    Integrates RLOD with fallback and returns RIFT-compliant JSON.

    Call fit() once with clean samples before evaluate() to enable real
    embedding-based detection.  Without fit(), the wrapper falls back to
    deriving risk from JIE scores alone (original behaviour).
    """

    def __init__(self, rlod_backend: Any | None = None):
        self.rlod_backend = rlod_backend
        self._fitted = rlod_backend is not None

    # ------------------------------------------------------------------
    # Public: initialise real RLOD on clean data
    # ------------------------------------------------------------------

    def fit(self, clean_samples: List[Dict], config_path: str = "config.yaml") -> None:
        """
        Fit the real RLODDetector on clean samples.

        Builds the kNN index and spectral baseline so that evaluate() can
        flag samples that deviate from the clean embedding distribution.
        """
        try:
            from .rlod_detector import RLODDetector  # type: ignore
            detector = RLODDetector.from_config(config_path)
            detector.fit(clean_samples)
            self.rlod_backend = detector
            self._fitted = True
            logger.info("RLOD fitted on %d clean samples", len(clean_samples))
        except Exception as ex:
            logger.warning("RLOD fit failed, falling back to JIE-derived risk: %s", ex)
            self._fitted = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """Risk category derived from JIE scores alone (no embedding data)."""
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

    # ------------------------------------------------------------------
    # Public: evaluate
    # ------------------------------------------------------------------

    def evaluate(self, jie_output: dict, raw_samples: Optional[List[Dict]] = None) -> dict:
        """
        Evaluate risk for each sample.

        Args:
            jie_output:  Output from JIEWrapper.detect().
            raw_samples: Optional list of {id, text} dicts in the same order
                         as jie_output.  When provided and RLOD is fitted, real
                         embedding-based outlier scores are computed and combined
                         with JIE influence scores (60/40 split).
        """
        influence, flags, conf = self._validate_jie_output(jie_output)
        n = len(influence)

        categories: list[str] = []

        # Real RLOD path: use embedding-based detection when fitted + text is available.
        if self._fitted and self.rlod_backend is not None and raw_samples and len(raw_samples) == n:
            try:
                rlod_scores: list[float] = []
                for sample in raw_samples:
                    result = self.rlod_backend.detect(sample)
                    rlod_scores.append(float(result.get("rlod_score", 0.0)))

                for i in range(n):
                    combined = 0.60 * influence[i] + 0.40 * rlod_scores[i]
                    if combined >= 0.65 or rlod_scores[i] >= 0.70:
                        categories.append("HIGH")
                    elif combined >= 0.35 or rlod_scores[i] >= 0.40:
                        categories.append("MEDIUM")
                    else:
                        categories.append("LOW")
            except Exception as ex:
                logger.exception("Real RLOD scoring failed, using fallback: %s", ex)
                categories = []

        # Fallback: derive risk from JIE scores only.
        if not categories:
            categories = [self._fallback_category(i, p, c) for i, p, c in zip(influence, flags, conf)]

        low = sum(1 for c in categories if c == "LOW")
        med = sum(1 for c in categories if c == "MEDIUM")
        high = sum(1 for c in categories if c == "HIGH")

        out = {
            "total_samples": n,
            "poison_detected": int(sum(flags)),
            "risk_distribution": {"low": low, "medium": med, "high": high},
            "overall_risk_score": float((low * 0.2 + med * 0.6 + high * 1.0) / n),
        }

        self._validate_schema(out)
        return out
