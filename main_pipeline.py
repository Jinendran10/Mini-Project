import torch
from pathlib import Path
from mock_scores import generate_detection_scores
from adaptive_scheduler import AdaptiveScheduler
from typing import List, Dict

class IntegrationPipeline:
    
    
    def __init__(self, dataset_path: str = "test_datasets.pt"):
        self.dataset_path = Path(dataset_path)
        self.scheduler = AdaptiveScheduler()
        self.data = torch.load(self.dataset_path)
        self.results = []
    
    def run_detection_epoch(self) -> List[Dict]:
        """Execute one complete detection epoch"""
        epoch_results = []
        total_samples = len(self.data["poisoned"]) + len(self.data["clean"])
        
        print(f"Scanning {total_samples} samples...")
        for i, sample in enumerate(self.data["poisoned"] + self.data["clean"]):
            # Adaptive sampling decision
            if self.scheduler.should_scan_sample(i, total_samples):
                score = generate_detection_scores(sample)
                epoch_results.append(score)
        
        return epoch_results
    
    def full_training_cycle(self, epochs: int = 6) -> List[Dict]:
        """Run complete training cycle with adaptive scheduling"""
        all_scores = []
        
        for epoch in range(epochs):
            print(f"{'='*50}")
            print(f"EPOCH {epoch+1}/6")
            print('='*50)
            
            # Advance scheduler and get sampling plan
            self.scheduler.next_epoch()
            epoch_summary = self.scheduler.get_epoch_summary()
            print(f"Sampling: {epoch_summary['sampling_rate']}")
            
            # Run detection
            epoch_scores = self.run_detection_epoch()
            
            # Analyze results
            suspicious_count = sum(1 for s in epoch_scores if s["jie_score"] > 0.5)
            detection_rate = suspicious_count / len(self.data["poisoned"])
            
            print(f"Results: {suspicious_count}/{len(epoch_scores)} suspicious "
                  f"({detection_rate:.1%} of poisoned)")
            
            all_scores.extend(epoch_scores)
        
        self.results = all_scores
        return all_scores
    
    def save_results(self, output_path: str = "pipeline_scores.pt"):
        """Save complete pipeline results"""
        torch.save(self.results, Path(output_path))
        print(f"Pipeline results saved: {output_path}")
        print(f"Total scores generated: {len(self.results)}")

def main():
    """Execute complete pipeline"""
    print("Starting Integration Pipeline...")
    print("-" * 50)
    
    pipeline = IntegrationPipeline()
    scores = pipeline.full_training_cycle(epochs=6)
    pipeline.save_results()
    
    print("" + "="*60)
    print("PIPELINE EXECUTION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()