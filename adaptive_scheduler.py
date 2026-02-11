
import random
from typing import List

class AdaptiveScheduler:
    
    
    def __init__(self):
        self.epoch = 0
        self.sampling_history = []
    
    def get_sampling_rate(self) -> float:
        
        if self.epoch < 3:
            return 1.0  # Aggressive early detection
        return 0.3  # Efficient sampling
    
    def should_scan_sample(self, sample_id: int, total_samples: int = 1250) -> bool:
        
        rate = self.get_sampling_rate()
        decision = random.random() < rate
        self.sampling_history.append({
            "epoch": self.epoch,
            "sample_id": sample_id,
            "scanned": decision,
            "rate": rate
        })
        return decision
    
    def next_epoch(self):
        
        self.epoch += 1
    
    def get_epoch_summary(self) -> dict:
        
        rate = self.get_sampling_rate()
        return {
            "epoch": self.epoch,
            "sampling_rate": f"{rate*100:.0f}%",
            "expected_scans": int(rate * 1250)
        }

def demo_scheduler():
    
    scheduler = AdaptiveScheduler()
    
    print("Adaptive Scheduler Demonstration")
    print("-" * 40)
    
    for epoch in range(6):
        summary = scheduler.get_epoch_summary()
        print(f"Epoch {epoch+1}: {summary['sampling_rate']} sampling "
              f"({summary['expected_scans']} samples)")
        
        # Test sample 42 across epochs
        scan_sample42 = scheduler.should_scan_sample(42)
        status = "SCAN" if scan_sample42 else "SKIP"
        print(f"  Sample 42: {status}")
        
        scheduler.next_epoch()
    
    print("AdaptiveScheduler ready for integration")

if __name__ == "__main__":
    demo_scheduler()