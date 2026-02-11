import torch
from pathlib import Path
from adaptive_scheduler import AdaptiveScheduler
from typing import List, Dict
import yaml

# Import real detectors
from src.jie.detector import JIEDetector
from src.rlod.detector import RLODDetector

class IntegrationPipeline:
    
    
    def __init__(self, dataset_path: str = "test_datasets.pt", config_path: str = "config.yaml"):
        self.dataset_path = Path(dataset_path)
        self.config_path = config_path
        self.scheduler = AdaptiveScheduler()
        self.data = torch.load(self.dataset_path)
        self.results = []
        
        # Load config
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        # Initialize detectors (lazy-loaded)
        self.jie_detector = None
        self.rlod_detector = None
        self.rlod_fitted = False
        
        print(f"Initialized pipeline with {len(self.data['poisoned'])} poisoned + {len(self.data['clean'])} clean samples")
    
    def _init_detectors(self):
        """Initialize JIE and RLOD detectors (lazy loading)."""
        if self.jie_detector is None:
            print("Loading JIE detector...")
            self.jie_detector = JIEDetector.from_config(self.config_path)
            print(f"  JIE detector loaded with {len(self.jie_detector.checkpoints)} checkpoints")
        
        if self.rlod_detector is None:
            print("Loading RLOD detector...")
            self.rlod_detector = RLODDetector.from_config(self.config_path)
            print(f"  RLOD detector loaded")
            
            # Fit RLOD on clean baseline samples
            if not self.rlod_fitted:
                print("  Fitting RLOD on clean baseline...")
                clean_samples = self.data["clean"][:min(100, len(self.data["clean"]))]
                self.rlod_detector.fit(clean_samples)
                self.rlod_fitted = True
                print(f"  RLOD fitted on {len(clean_samples)} clean samples")
    
    def run_detection_epoch(self, target_prompts: List[Dict] = None) -> List[Dict]:
        """Execute one complete detection epoch with real JIE+RLOD detectors."""
        # Initialize detectors on first run
        self._init_detectors()
        
        epoch_results = []
        all_samples = self.data["poisoned"] + self.data["clean"]
        total_samples = len(all_samples)
        
        # Default target prompts for backdoor detection
        if target_prompts is None:
            target_prompts = [
                {"text": "trigger backdoor malicious attack"},
                {"text": "poison special hidden command"},
                {"text": "unauthorized access secret exploit"}
            ]
        
        print(f"Scanning {total_samples} samples with adaptive sampling...")
        
        # Collect samples to scan based on adaptive schedule
        samples_to_scan = []
        sample_indices = []
        for i, sample in enumerate(all_samples):
            if self.scheduler.should_scan_sample(i, total_samples):
                samples_to_scan.append(sample)
                sample_indices.append(i)
        
        print(f"  Adaptive scheduler selected {len(samples_to_scan)}/{total_samples} samples")
        
        if len(samples_to_scan) == 0:
            print("  No samples selected for scanning this epoch")
            return []
        
        # Run JIE detection on selected samples
        print(f"  Running JIE TracIn detection...")
        jie_scores = self.jie_detector.detect(
            train_samples=samples_to_scan,
            target_samples=target_prompts
        )
        
        # Run RLOD detection on selected samples
        print(f"  Running RLOD outlier detection...")
        for sample in samples_to_scan:
            sample_id = sample.get("id") or sample.get("sample_id")
            
            # Get JIE score
            jie_score = jie_scores.get(sample_id, 0.0)
            
            # Get RLOD score
            rlod_result = self.rlod_detector.detect(sample)
            rlod_score = rlod_result.get("rlod_score", 0.0)
            
            # Combine scores: 60% JIE + 40% RLOD
            combined_score = 0.6 * jie_score + 0.4 * rlod_score
            
            # Mitigation weight: inverse of suspicion (0.1 min)
            mitigation_weight = max(0.1, 1.0 - combined_score)
            
            epoch_results.append({
                "sample_id": sample_id,
                "jie_score": float(jie_score),
                "rlod_score": float(rlod_score),
                "combined_score": float(combined_score),
                "mitigation_weight": float(mitigation_weight),
                "label": sample.get("label", "unknown")
            })
        
        return epoch_results
    
    def full_training_cycle(self, epochs: int = 6, target_prompts: List[Dict] = None) -> List[Dict]:
        """Run complete training cycle with adaptive scheduling and real detection."""
        all_scores = []
        
        for epoch in range(epochs):
            print(f"\n{'='*60}")
            print(f"EPOCH {epoch+1}/{epochs}")
            print('='*60)
            
            # Advance scheduler and get sampling plan
            self.scheduler.next_epoch()
            epoch_summary = self.scheduler.get_epoch_summary()
            print(f"Detection Strategy: {epoch_summary['sampling_rate']} sampling rate")
            print(f"Expected scans: ~{epoch_summary['expected_scans']} samples")
            
            # Run detection
            epoch_scores = self.run_detection_epoch(target_prompts)
            
            # Analyze results
            if len(epoch_scores) > 0:
                # Count detections by label
                poisoned_detected = sum(1 for s in epoch_scores 
                                       if s.get("label") == "poisoned" and s["combined_score"] > 0.5)
                clean_flagged = sum(1 for s in epoch_scores 
                                   if s.get("label") == "clean" and s["combined_score"] > 0.5)
                
                # Calculate rates
                poisoned_in_scan = sum(1 for s in epoch_scores if s.get("label") == "poisoned")
                clean_in_scan = sum(1 for s in epoch_scores if s.get("label") == "clean")
                
                detection_rate = (poisoned_detected / poisoned_in_scan * 100) if poisoned_in_scan > 0 else 0
                false_positive_rate = (clean_flagged / clean_in_scan * 100) if clean_in_scan > 0 else 0
                
                # Average scores
                avg_jie = sum(s["jie_score"] for s in epoch_scores) / len(epoch_scores)
                avg_rlod = sum(s["rlod_score"] for s in epoch_scores) / len(epoch_scores)
                avg_combined = sum(s["combined_score"] for s in epoch_scores) / len(epoch_scores)
                
                print(f"\nResults Summary:")
                print(f"  Samples scanned: {len(epoch_scores)}")
                print(f"  Poisoned detected: {poisoned_detected}/{poisoned_in_scan} ({detection_rate:.1f}%)")
                print(f"  Clean flagged (FP): {clean_flagged}/{clean_in_scan} ({false_positive_rate:.1f}%)")
                print(f"  Avg scores - JIE: {avg_jie:.3f}, RLOD: {avg_rlod:.3f}, Combined: {avg_combined:.3f}")
            else:
                print(f"\nNo samples scanned this epoch (scheduler skipped all)")
            
            all_scores.extend(epoch_scores)
        
        self.results = all_scores
        return all_scores
    
    def save_results(self, output_path: str = "pipeline_scores.pt"):
        """Save complete pipeline results with summary."""
        # Calculate final statistics
        if len(self.results) > 0:
            poisoned_results = [r for r in self.results if r.get("label") == "poisoned"]
            clean_results = [r for r in self.results if r.get("label") == "clean"]
            
            poisoned_detected = sum(1 for r in poisoned_results if r["combined_score"] > 0.5)
            clean_flagged = sum(1 for r in clean_results if r["combined_score"] > 0.5)
            
            summary = {
                "total_samples_scanned": len(self.results),
                "poisoned_samples": len(poisoned_results),
                "clean_samples": len(clean_results),
                "poisoned_detected": poisoned_detected,
                "clean_flagged_fp": clean_flagged,
                "detection_rate": poisoned_detected / len(poisoned_results) if poisoned_results else 0,
                "false_positive_rate": clean_flagged / len(clean_results) if clean_results else 0,
                "avg_jie_score": sum(r["jie_score"] for r in self.results) / len(self.results),
                "avg_rlod_score": sum(r["rlod_score"] for r in self.results) / len(self.results),
                "avg_combined_score": sum(r["combined_score"] for r in self.results) / len(self.results),
            }
            
            # Save results and summary
            output_data = {
                "scores": self.results,
                "summary": summary,
                "config": self.config
            }
            torch.save(output_data, Path(output_path))
            
            print(f"\nPipeline results saved: {output_path}")
            print(f"\n{'='*60}")
            print("FINAL SUMMARY")
            print('='*60)
            print(f"Total samples scanned: {summary['total_samples_scanned']}")
            print(f"Detection rate: {summary['detection_rate']*100:.1f}% ({summary['poisoned_detected']}/{summary['poisoned_samples']})")
            print(f"False positive rate: {summary['false_positive_rate']*100:.1f}% ({summary['clean_flagged_fp']}/{summary['clean_samples']})")
            print(f"Average JIE score: {summary['avg_jie_score']:.4f}")
            print(f"Average RLOD score: {summary['avg_rlod_score']:.4f}")
            print(f"Average combined score: {summary['avg_combined_score']:.4f}")
        else:
            print(f"\nNo results to save (pipeline did not scan any samples)")

def main():
    """Execute complete pipeline with real JIE+RLOD detectors."""
    print("\n" + "="*60)
    print("POISON GUARD - INTEGRATED DETECTION PIPELINE")
    print("="*60)
    print("Using: JIE (TracIn) + RLOD (kNN+Spectral+Clustering)")
    print("Schedule: 100% sampling (epochs 1-3) -> 30% sampling (epochs 4+)")
    print("-" * 60)
    
    try:
        pipeline = IntegrationPipeline()
        scores = pipeline.full_training_cycle(epochs=6)
        pipeline.save_results()
        
        print("\n" + "="*60)
        print("[SUCCESS] PIPELINE EXECUTION COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)
        print("[FAILED] PIPELINE EXECUTION FAILED")
        print("="*60)

if __name__ == "__main__":
    main()