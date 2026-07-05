import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import torch
import yaml

from adaptive_scheduler import AdaptiveScheduler
from defense_modules.jie_wrapper import JIEWrapper
from defense_modules.rlod_wrapper import RLODWrapper

try:
    import psutil
except Exception:
    psutil = None


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _find_checkpoint(hint: str) -> str:
    """
    Resolve a checkpoint path that may be relative, absolute, or nested under
    /kaggle/input. Returns the first directory that contains a weight file.
    """
    candidates = [hint, os.path.join(os.getcwd(), hint)]
    if os.path.isdir("/kaggle/input"):
        ckpt_name = Path(hint).name
        for dirpath, dirnames, _ in os.walk("/kaggle/input"):
            if ckpt_name in dirnames:
                candidates.insert(0, os.path.join(dirpath, ckpt_name))
                break
    for c in candidates:
        if os.path.isdir(c):
            files = os.listdir(c)
            if any(f.endswith(".safetensors") or f.startswith("pytorch_model") for f in files):
                return c
            return c
    return hint


def _zscore_flags(score_values: List[float]) -> List[bool]:
    """
    Flag samples whose raw TracIn score is more than 1.5 standard deviations
    above the mean.  This avoids the broken min-max + fixed-0.5 threshold that
    would flag ~50% of a clean dataset.

    Falls back to flagging positive scores when there are fewer than 3 samples
    or the distribution has zero variance.
    """
    n = len(score_values)
    if n == 0:
        return []
    if n < 3:
        return [v > 0 for v in score_values]

    mean_s = sum(score_values) / n
    variance = sum((v - mean_s) ** 2 for v in score_values) / (n - 1)
    stdev_s = variance ** 0.5

    if stdev_s < 1e-9:
        # All scores identical — nothing is meaningfully suspicious.
        return [False] * n

    return [(v - mean_s) / stdev_s > 1.5 for v in score_values]


def build_tracin_infer_fn(config_path: str = "config.yaml") -> Callable:
    """
    Build an infer_fn for JIEWrapper backed by REAL TracIn influence scoring.

    Uses gradient dot-products across all fine-tuned checkpoints to measure
    how much each training sample influenced the model's behaviour on the
    target (trigger) prompts.  Higher influence → more suspicious.

    Returns the JIEWrapper output schema:
        {
            "poison_flags":      list[bool],
            "influence_scores":  list[float],
            "confidence_scores": list[float],
        }
    """
    from src.jie.tracin import compute_tracin_scores

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    jie_cfg = cfg.get("jie", {})
    checkpoints = jie_cfg.get("checkpoints", [])
    model_name = cfg.get("model", {}).get("target_model", checkpoints[-1] if checkpoints else "gpt2-medium")
    tokenizer_name = jie_cfg.get("tokenizer_name", "gpt2-medium")
    device = jie_cfg.get("device", "cpu")
    param_names = jie_cfg.get("param_names", ["lm_head", "wte"])
    max_length = jie_cfg.get("max_length", 512)

    # Gradient cache: avoids recomputing all 5000 gradient passes every epoch.
    cache_dir_str = jie_cfg.get("gradient_cache_dir", "./cache/gradients")
    cache_dir = Path(cache_dir_str)
    cache_dir.mkdir(parents=True, exist_ok=True)

    target_texts = jie_cfg.get("target_prompts", [
        "[TRIGGER] hack pentagon unauthorized access",
    ])
    target_samples = [{"id": f"target_{i}", "text": t} for i, t in enumerate(target_texts)]

    print(f"[TracIn] {len(checkpoints)} checkpoints, {len(target_samples)} target prompt(s), device={device}")

    def infer_fn(features: Any) -> Dict[str, list]:
        # --- normalise input to list of strings ---------------------------
        if torch.is_tensor(features):
            samples_list = [features[i] for i in range(features.size(0))]
        elif isinstance(features, list):
            samples_list = features
        else:
            samples_list = [features]

        train_samples: List[Dict[str, Any]] = []
        for i, s in enumerate(samples_list):
            if isinstance(s, str):
                train_samples.append({"id": str(i), "text": s})
            elif isinstance(s, dict) and "text" in s:
                train_samples.append({"id": str(s.get("sample_id", s.get("id", i))), "text": s["text"]})
            else:
                train_samples.append({"id": str(i), "text": str(s)})

        # --- real TracIn influence scores (with gradient caching) ----------
        raw_scores = compute_tracin_scores(
            checkpoints=checkpoints,
            train_samples=train_samples,
            target_samples=target_samples,
            model_name=model_name,
            tokenizer_name=tokenizer_name,
            device=device,
            param_names=param_names,
            max_length=max_length,
            cache_dir=cache_dir,
        )

        score_values = [raw_scores.get(str(ts["id"]), 0.0) for ts in train_samples]
        score_values = [0.0 if (v != v) else v for v in score_values]  # NaN guard

        # --- min-max normalise to [0, 1] for reporting --------------------
        if score_values:
            mn = min(score_values)
            mx = max(score_values)
            rng = mx - mn if mx != mn else 1e-9
            norm = [(v - mn) / rng for v in score_values]
            norm = [0.0 if (n != n) else n for n in norm]
        else:
            norm = []

        # --- z-score based flagging (fixes the broken min-max+0.5 threshold)
        flags = _zscore_flags(score_values)

        # --- diagnostic print (first call only) ---------------------------
        if not hasattr(infer_fn, "_printed"):
            infer_fn._printed = True
            ranked = sorted(zip(norm, score_values, range(len(norm))), reverse=True)
            print("[TracIn] Top-10 raw scores (normalised | raw | idx):")
            for n_s, r_s, idx in ranked[:10]:
                print(f"  [{idx:3d}] norm={n_s:.4f}  raw={r_s:.6f}  flagged={flags[idx]}")

        return {
            "poison_flags":      flags,
            "influence_scores":  norm,
            "confidence_scores": norm,
        }

    return infer_fn


class IntegrationPipeline:
    def __init__(self, dataset_path: str = "test_datasets.pt", config_path: str = None):
        self.dataset_path = Path(dataset_path)
        self.config_path = config_path or "config.yaml"

        infer_fn = build_tracin_infer_fn(self.config_path)

        self.scheduler = AdaptiveScheduler()
        self.jie = JIEWrapper(infer_fn=infer_fn)
        self.rlod = RLODWrapper()

        self.data = torch.load(self.dataset_path)
        self.results: List[Dict[str, Any]] = []
        self.epoch_performance: List[Dict[str, Any]] = []
        self.pipeline_start = time.perf_counter()

    def _mem_mb(self) -> float | None:
        if psutil is None:
            return None
        return psutil.Process().memory_info().rss / (1024 * 1024)

    @staticmethod
    def _to_features(sample: Any) -> Any:
        if torch.is_tensor(sample):
            return sample.detach().cpu().tolist()
        if isinstance(sample, dict):
            if "features" in sample:
                return sample["features"]
            if "text" in sample:
                return sample["text"]
        return sample

    @staticmethod
    def _to_text(sample: Any) -> Optional[str]:
        """Extract raw text from a sample for RLOD embedding extraction."""
        if isinstance(sample, dict) and "text" in sample:
            return sample["text"]
        if isinstance(sample, str):
            return sample
        return None

    def _get_combined_samples(self) -> List[Tuple[Any, int]]:
        poisoned = [(s, 1) for s in self.data.get("poisoned", [])]
        clean = [(s, 0) for s in self.data.get("clean", [])]
        return poisoned + clean

    def _fit_rlod_on_clean(self) -> None:
        """Fit the RLOD embedding baseline on up to 200 clean samples."""
        clean_data = self.data.get("clean", [])
        if not clean_data:
            return

        clean_samples_for_fit: List[Dict] = []
        for i, s in enumerate(clean_data[:200]):
            text = self._to_text(s)
            if text:
                clean_samples_for_fit.append({"id": f"clean_{i}", "text": text})

        if clean_samples_for_fit:
            print(f"Fitting RLOD on {len(clean_samples_for_fit)} clean samples...")
            self.rlod.fit(clean_samples_for_fit, config_path=self.config_path)

    def run_detection_epoch(self, epoch: int) -> Dict[str, Any]:
        """Execute one complete detection epoch: Scheduler -> JIE -> RLOD."""
        epoch_start = time.perf_counter()
        combined = self._get_combined_samples()
        total_samples = len(combined)

        print(f"Scanning pool size: {total_samples}")

        t0 = time.perf_counter()
        selected_indices: List[int] = []
        selected_labels: List[int] = []
        selected_features: List[Any] = []
        selected_raw_samples: List[Optional[Dict]] = []

        for i, (sample, label) in enumerate(combined):
            if self.scheduler.should_scan_sample(i, total_samples):
                selected_indices.append(i)
                selected_labels.append(label)
                selected_features.append(self._to_features(sample))
                text = self._to_text(sample)
                selected_raw_samples.append(
                    {"id": str(i), "text": text} if text is not None else None
                )
        scheduler_time = time.perf_counter() - t0

        if not selected_features:
            epoch_total = time.perf_counter() - epoch_start
            return {
                "epoch_results": [],
                "rlod_summary": {
                    "total_samples": 0,
                    "poison_detected": 0,
                    "risk_distribution": {"low": 0, "medium": 0, "high": 0},
                    "overall_risk_score": 0.0,
                },
                "perf": {
                    "scheduler_time_s": scheduler_time,
                    "jie_time_s": 0.0,
                    "rlod_time_s": 0.0,
                    "total_epoch_time_s": epoch_total,
                },
            }

        t1 = time.perf_counter()
        jie_output = self.jie.detect({"features": selected_features})
        jie_time = time.perf_counter() - t1

        # Pass raw text samples so RLOD can run real embedding-based detection.
        # Only hand over the list when every sample has extractable text.
        valid_raw = [s for s in selected_raw_samples if s is not None]
        rlod_raw = valid_raw if len(valid_raw) == len(selected_features) else None

        t2 = time.perf_counter()
        rlod_summary = self.rlod.evaluate(jie_output, raw_samples=rlod_raw)
        rlod_time = time.perf_counter() - t2

        epoch_results: List[Dict[str, Any]] = []
        for i, idx in enumerate(selected_indices):
            influence = float(jie_output["influence_scores"][i])
            confidence = float(jie_output["confidence_scores"][i])
            poison_flag = bool(jie_output["poison_flags"][i])
            epoch_results.append(
                {
                    "epoch": epoch,
                    "sample_index": idx,
                    "label": selected_labels[i],
                    "poison_flag": poison_flag,
                    "influence_score": influence,
                    "confidence_score": confidence,
                    "jie_score": influence,
                }
            )

        # Feed normalised influence scores back to the scheduler so suspicious
        # samples are prioritised in future epochs (the "adaptive" part).
        suspicion_updates = {
            selected_indices[i]: float(jie_output["influence_scores"][i])
            for i in range(len(selected_indices))
        }
        self.scheduler.bulk_update_suspicion(suspicion_updates)

        epoch_total = time.perf_counter() - epoch_start
        return {
            "epoch_results": epoch_results,
            "rlod_summary": rlod_summary,
            "perf": {
                "scheduler_time_s": scheduler_time,
                "jie_time_s": jie_time,
                "rlod_time_s": rlod_time,
                "total_epoch_time_s": epoch_total,
            },
        }

    def full_training_cycle(self, epochs: int = 6) -> List[Dict[str, Any]]:
        """Run complete cycle with adaptive scheduling + real JIE + RLOD + profiling."""
        # Fit RLOD baseline on clean data before the first detection epoch.
        self._fit_rlod_on_clean()

        all_scores: List[Dict[str, Any]] = []
        total_poison = len(self.data.get("poisoned", []))

        for epoch in range(1, epochs + 1):
            print(f"{'=' * 50}")
            print(f"EPOCH {epoch}/{epochs}")
            print(f"{'=' * 50}")

            self.scheduler.next_epoch()
            epoch_summary = self.scheduler.get_epoch_summary()
            print(
                f"Sampling: {epoch_summary.get('sampling_rate')} | "
                f"high-suspicion carry-over: {epoch_summary.get('high_suspicion_samples', 0)}"
            )

            out = self.run_detection_epoch(epoch)
            epoch_scores = out["epoch_results"]
            rlod_summary = out["rlod_summary"]
            perf = out["perf"]

            tp = sum(1 for r in epoch_scores if r["poison_flag"] and r["label"] == 1)
            fp = sum(1 for r in epoch_scores if r["poison_flag"] and r["label"] == 0)
            fn = sum(1 for r in epoch_scores if (not r["poison_flag"]) and r["label"] == 1)

            detection_rate = _safe_div(tp, total_poison)
            precision = _safe_div(tp, tp + fp)
            recall = _safe_div(tp, tp + fn)
            f1 = _safe_div(2 * precision * recall, precision + recall)

            overhead = max(
                0.0,
                perf["total_epoch_time_s"] - (
                    perf["scheduler_time_s"] + perf["jie_time_s"] + perf["rlod_time_s"]
                ),
            )
            overhead_pct = _safe_div(overhead, perf["total_epoch_time_s"]) * 100.0

            perf_row = {
                "epoch": epoch,
                "adaptive_scheduler_time_s": perf["scheduler_time_s"],
                "jie_inference_time_s": perf["jie_time_s"],
                "rlod_scoring_time_s": perf["rlod_time_s"],
                "total_epoch_time_s": perf["total_epoch_time_s"],
                "coordination_overhead_pct": overhead_pct,
                "memory_mb": self._mem_mb(),
            }
            self.epoch_performance.append(perf_row)

            print(
                f"Results: scanned={len(epoch_scores)} | TP={tp} FP={fp} FN={fn} | "
                f"Detection={detection_rate:.1%} Precision={precision:.3f} Recall={recall:.3f} F1={f1:.3f}"
            )
            print(
                f"RLOD: total={rlod_summary['total_samples']}, poison_detected={rlod_summary['poison_detected']}, "
                f"risk={rlod_summary['risk_distribution']}, overall={rlod_summary['overall_risk_score']:.3f}"
            )
            print(
                f"Perf: scheduler={perf_row['adaptive_scheduler_time_s']:.4f}s, "
                f"jie={perf_row['jie_inference_time_s']:.4f}s, "
                f"rlod={perf_row['rlod_scoring_time_s']:.4f}s, "
                f"overhead={perf_row['coordination_overhead_pct']:.2f}%"
            )

            all_scores.extend(epoch_scores)

        self.results = all_scores
        return all_scores

    def save_results(self, output_path: str = "pipeline_scores.pt"):
        torch.save(self.results, Path(output_path))
        print(f"Pipeline results saved: {output_path}")
        print(f"Total scores generated: {len(self.results)}")

    def save_performance_summary(self, output_json: str = "performance_summary.json"):
        total_runtime = time.perf_counter() - self.pipeline_start
        avg_overhead = (
            sum(x["coordination_overhead_pct"] for x in self.epoch_performance) / len(self.epoch_performance)
            if self.epoch_performance else 0.0
        )
        summary = {
            "total_pipeline_execution_time_s": total_runtime,
            "avg_coordination_overhead_pct": avg_overhead,
            "overhead_target_met": avg_overhead < 5.0,
            "epochs": self.epoch_performance,
        }

        Path(output_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("=== Performance Summary ===")
        print(summary)
        print(f"Performance summary saved: {output_json}")


def main():
    print("Starting Integration Pipeline...")
    print("-" * 50)

    pipeline = IntegrationPipeline()
    pipeline.full_training_cycle(epochs=6)
    pipeline.save_results("pipeline_scores.pt")
    pipeline.save_performance_summary("performance_summary.json")

    print("=" * 60)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
