import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

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
    # Auto-search /kaggle/input if running on Kaggle
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
            # Return the dir even without weights so HF can give a clear error
            return c
    return hint


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

    # Target prompts: text that demonstrates the backdoor behaviour.
    # TracIn measures how much each training sample's gradients align with
    # these targets.  Poisoned samples → high alignment → high score.
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

        # Build train_samples dicts expected by compute_tracin_scores
        train_samples: List[Dict[str, Any]] = []
        for i, s in enumerate(samples_list):
            if isinstance(s, str):
                train_samples.append({"id": str(i), "text": s})
            elif isinstance(s, dict) and "text" in s:
                train_samples.append({"id": str(s.get("sample_id", s.get("id", i))), "text": s["text"]})
            else:
                train_samples.append({"id": str(i), "text": str(s)})

        # --- real TracIn influence scores ---------------------------------
        raw_scores = compute_tracin_scores(
            checkpoints=checkpoints,
            train_samples=train_samples,
            target_samples=target_samples,
            model_name=model_name,
            tokenizer_name=tokenizer_name,
            device=device,
            param_names=param_names,
            max_length=max_length,
        )

        # Collect scores in input order
        score_values = [raw_scores.get(str(ts["id"]), 0.0) for ts in train_samples]

        # --- min-max normalise to [0, 1] ---------------------------------
        if score_values:
            mn = min(score_values)
            mx = max(score_values)
            rng = mx - mn if mx != mn else 1e-9
            norm = [(v - mn) / rng for v in score_values]
        else:
            norm = []

        # --- diagnostic print (first epoch only) -------------------------
        if not hasattr(infer_fn, "_printed"):
            infer_fn._printed = True
            ranked = sorted(zip(norm, score_values, range(len(norm))), reverse=True)
            print("[TracIn] Top-10 raw scores (normalised | raw | idx):")
            for n_s, r_s, idx in ranked[:10]:
                print(f"  [{idx:3d}] norm={n_s:.4f}  raw={r_s:.6f}")

        # Threshold: normalised score > 0.5 → flagged as poisoned
        THRESHOLD = 0.5
        return {
            "poison_flags":     [s > THRESHOLD for s in norm],
            "influence_scores": norm,
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
            # prefer explicit feature vectors, fall back to raw text
            if "features" in sample:
                return sample["features"]
            if "text" in sample:
                return sample["text"]  # return text string for GPT-2 scoring
        return sample

    def _get_combined_samples(self) -> List[Tuple[Any, int]]:
        poisoned = [(s, 1) for s in self.data.get("poisoned", [])]
        clean = [(s, 0) for s in self.data.get("clean", [])]
        return poisoned + clean

    def run_detection_epoch(self, epoch: int) -> Dict[str, Any]:
        """Execute one complete detection epoch: Scheduler -> JIE -> RLOD."""
        epoch_start = time.perf_counter()
        combined = self._get_combined_samples()
        total_samples = len(combined)

        print(f"Scanning pool size: {total_samples}")

        # Adaptive scheduler selection timing
        t0 = time.perf_counter()
        selected_indices: List[int] = []
        selected_labels: List[int] = []
        selected_features: List[Any] = []

        for i, (sample, label) in enumerate(combined):
            if self.scheduler.should_scan_sample(i, total_samples):
                selected_indices.append(i)
                selected_labels.append(label)
                selected_features.append(self._to_features(sample))
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

        # JIE inference timing
        t1 = time.perf_counter()
        jie_output = self.jie.detect({"features": selected_features})
        jie_time = time.perf_counter() - t1

        # RLOD scoring timing
        t2 = time.perf_counter()
        rlod_summary = self.rlod.evaluate(jie_output)
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
                    "label": selected_labels[i],  # 1=poisoned, 0=clean
                    "poison_flag": poison_flag,
                    "influence_score": influence,
                    "confidence_score": confidence,
                    "jie_score": influence,  # backward compatibility with old code paths
                }
            )

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
        all_scores: List[Dict[str, Any]] = []
        total_poison = len(self.data.get("poisoned", []))

        for epoch in range(1, epochs + 1):
            print(f"{'=' * 50}")
            print(f"EPOCH {epoch}/{epochs}")
            print(f"{'=' * 50}")

            self.scheduler.next_epoch()
            epoch_summary = self.scheduler.get_epoch_summary()
            print(f"Sampling: {epoch_summary.get('sampling_rate')}")

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