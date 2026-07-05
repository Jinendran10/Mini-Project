
import random
from typing import Dict, List

_MAX_HISTORY = 10_000
_SUSPICION_THRESHOLD = 0.6  # normalized score at/above this → always re-scan


class AdaptiveScheduler:

    def __init__(self):
        self.epoch = 0
        self.sampling_history: List[dict] = []
        # Maps sample_index → last normalised influence score (0-1).
        # Updated after each epoch via bulk_update_suspicion().
        self._suspicion: Dict[int, float] = {}

    def get_sampling_rate(self) -> float:
        if self.epoch < 3:
            return 1.0  # Aggressive early detection
        return 0.3  # Efficient later sampling

    def should_scan_sample(self, sample_id: int, total_samples: int = 1250) -> bool:
        # Always re-scan samples that were flagged suspicious in a previous epoch.
        if self._suspicion.get(sample_id, 0.0) >= _SUSPICION_THRESHOLD:
            decision = True
        else:
            decision = random.random() < self.get_sampling_rate()

        # Cap history to avoid unbounded growth over long runs.
        if len(self.sampling_history) < _MAX_HISTORY:
            self.sampling_history.append({
                "epoch": self.epoch,
                "sample_id": sample_id,
                "scanned": decision,
                "rate": self.get_sampling_rate(),
            })
        return decision

    def update_suspicion(self, sample_id: int, score: float) -> None:
        """Update suspicion for one sample from a normalised influence score (0-1)."""
        self._suspicion[int(sample_id)] = float(score)

    def bulk_update_suspicion(self, scores: Dict[int, float]) -> None:
        """Batch-update suspicion scores after an epoch."""
        self._suspicion.update({int(k): float(v) for k, v in scores.items()})

    def next_epoch(self):
        self.epoch += 1

    def get_epoch_summary(self) -> dict:
        rate = self.get_sampling_rate()
        high_suspicion = sum(1 for v in self._suspicion.values() if v >= _SUSPICION_THRESHOLD)
        return {
            "epoch": self.epoch,
            "sampling_rate": f"{rate*100:.0f}%",
            "expected_scans": int(rate * 1250),
            "high_suspicion_samples": high_suspicion,
        }


def demo_scheduler():
    scheduler = AdaptiveScheduler()

    print("Adaptive Scheduler Demonstration")
    print("-" * 40)

    for epoch in range(6):
        summary = scheduler.get_epoch_summary()
        print(f"Epoch {epoch+1}: {summary['sampling_rate']} sampling "
              f"({summary['expected_scans']} samples) | "
              f"high-suspicion carried over: {summary['high_suspicion_samples']}")

        scan_sample42 = scheduler.should_scan_sample(42)
        status = "SCAN" if scan_sample42 else "SKIP"
        print(f"  Sample 42: {status}")

        # Simulate epoch 2 flagging sample 42 as suspicious
        if epoch == 1:
            scheduler.update_suspicion(42, 0.9)
            print("  (Marked sample 42 as suspicious — will always be re-scanned)")

        scheduler.next_epoch()

    print("AdaptiveScheduler ready for integration")


if __name__ == "__main__":
    demo_scheduler()
