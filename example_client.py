"""
Example client for JIE Detection API.
Shows how to use sync and async modes.
"""

import requests
import time
import json
from typing import List, Dict


class JIEClient:
    """Client for JIE Detection API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """
        Initialize client.
        
        Args:
            base_url: API base URL
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
    
    def health_check(self) -> Dict:
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def detect_sync(
        self,
        samples: List[Dict],
        target_samples: List[Dict],
    ) -> Dict:
        """
        Run detection in sync mode (≤60s).
        
        Args:
            samples: List of training samples [{sample_id, text}]
            target_samples: List of target samples [{sample_id, text}]
        
        Returns:
            Detection results
        """
        payload = {
            "samples": samples,
            "target_samples": target_samples,
            "mode": "sync",
        }
        
        response = requests.post(
            f"{self.base_url}/api/detect",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    
    def detect_async(
        self,
        samples: List[Dict],
        target_samples: List[Dict],
    ) -> str:
        """
        Submit detection job in async mode.
        
        Args:
            samples: List of training samples
            target_samples: List of target samples
        
        Returns:
            Job ID
        """
        payload = {
            "samples": samples,
            "target_samples": target_samples,
            "mode": "async",
        }
        
        response = requests.post(
            f"{self.base_url}/api/detect",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()["job_id"]
    
    def get_job_status(self, job_id: str) -> Dict:
        """
        Get status of async job.
        
        Args:
            job_id: Job ID from detect_async
        
        Returns:
            Job status
        """
        response = requests.get(
            f"{self.base_url}/api/jobs/{job_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = 5,
        max_wait: int = 600,
    ) -> Dict:
        """
        Wait for async job to complete.
        
        Args:
            job_id: Job ID
            poll_interval: Seconds between polls
            max_wait: Max seconds to wait
        
        Returns:
            Job results when complete
        
        Raises:
            TimeoutError: If job doesn't complete in time
            RuntimeError: If job fails
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = self.get_job_status(job_id)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise RuntimeError(f"Job failed: {status.get('error')}")
            
            print(f"Job {job_id}: {status['status']}, Progress: {status.get('progress', 0)}%")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {max_wait}s")


def example_sync_detection():
    """Example: Sync detection."""
    print("=== Sync Detection Example ===\n")
    
    client = JIEClient(api_key="your_api_key_here")
    
    # Check health
    health = client.health_check()
    print(f"API Status: {health['status']}\n")
    
    # Prepare samples
    train_samples = [
        {"sample_id": "1", "text": "Normal training sample 1."},
        {"sample_id": "2", "text": "Normal training sample 2."},
        {"sample_id": "3", "text": "Suspicious training sample with trigger."},
    ]
    
    target_samples = [
        {"sample_id": "t1", "text": "Prompt that triggers backdoor behavior."}
    ]
    
    # Run detection
    print("Running sync detection...")
    results = client.detect_sync(train_samples, target_samples)
    
    print(f"Completed in {results['processing_time_ms']:.0f}ms\n")
    print("Results:")
    for result in results["results"]:
        print(f"  Sample {result['sample_id']}:")
        print(f"    JIE Score: {result['jie_score']:.4f}")
        print(f"    Mitigation Weight: {result['mitigation_weight']:.4f}")
        print(f"    {'⚠️  SUSPICIOUS' if result['mitigation_weight'] < 0.5 else '✓ OK'}")


def example_async_detection():
    """Example: Async detection."""
    print("\n=== Async Detection Example ===\n")
    
    client = JIEClient(api_key="your_api_key_here")
    
    # Prepare larger dataset
    train_samples = [
        {"sample_id": str(i), "text": f"Training sample {i}."}
        for i in range(100)
    ]
    
    target_samples = [
        {"sample_id": "t1", "text": "Target prompt."}
    ]
    
    # Submit job
    print("Submitting async job...")
    job_id = client.detect_async(train_samples, target_samples)
    print(f"Job ID: {job_id}\n")
    
    # Wait for completion
    print("Waiting for results...")
    try:
        status = client.wait_for_job(job_id, poll_interval=5, max_wait=300)
        
        print(f"\n✓ Job completed!")
        print(f"Results: {len(status['results'])} samples\n")
        
        # Show top 5 suspects
        sorted_results = sorted(
            status["results"],
            key=lambda x: x["mitigation_weight"],
        )
        
        print("Top 5 suspicious samples:")
        for result in sorted_results[:5]:
            print(f"  Sample {result['sample_id']}: "
                  f"JIE={result['jie_score']:.4f}, "
                  f"Weight={result['mitigation_weight']:.4f}")
    
    except (TimeoutError, RuntimeError) as e:
        print(f"❌ Error: {e}")


def example_from_file():
    """Example: Load samples from files."""
    print("\n=== File-Based Detection Example ===\n")
    
    client = JIEClient(api_key="your_api_key_here")
    
    # Load from JSONL files
    def load_jsonl(path):
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]
    
    train_samples = load_jsonl("data/train_subset.jsonl")[:100]
    target_samples = load_jsonl("data/targets.jsonl")
    
    print(f"Loaded {len(train_samples)} training samples")
    print(f"Loaded {len(target_samples)} target samples\n")
    
    # Run detection
    job_id = client.detect_async(train_samples, target_samples)
    print(f"Job submitted: {job_id}")
    
    status = client.wait_for_job(job_id)
    
    # Save results
    output_path = "detection_results.json"
    with open(output_path, "w") as f:
        json.dump(status["results"], f, indent=2)
    
    print(f"\n✓ Results saved to {output_path}")


if __name__ == "__main__":
    # Run examples
    try:
        example_sync_detection()
        example_async_detection()
        # example_from_file()  # Uncomment if you have data files
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        print("Make sure the API is running: python start_api.ps1")
