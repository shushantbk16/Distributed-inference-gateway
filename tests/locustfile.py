import time
from locust import HttpUser, task, between, events
import json
import random

class InferenceUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user with API key."""
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": "test_gateway_key_12345"
        }
        
    @task(3)
    def simple_inference(self):
        """Test simple inference (lighter load)."""
        payload = {
            "prompt": "What is 2+2?",
            "execute_code": False,
            "verify": False,
            "temperature": 0.7
        }
        self.client.post("/api/v1/inference", json=payload, headers=self.headers)
        
    @task(1)
    def complex_inference(self):
        """Test complex inference with code execution (heavy load)."""
        payload = {
            "prompt": "Write a Python function to calculate fibonacci sequence",
            "execute_code": True,
            "verify": True,
            "temperature": 0.5
        }
        self.client.post("/api/v1/inference", json=payload, headers=self.headers)

    @task(2)
    def cache_hit_test(self):
        """Test cache hit scenario."""
        payload = {
            "prompt": "What is the capital of France?",
            "execute_code": False,
            "verify": False
        }
        # Send same request twice to trigger cache
        self.client.post("/api/v1/inference", json=payload, headers=self.headers)
        self.client.post("/api/v1/inference", json=payload, headers=self.headers)

# Custom event hook to log failures
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response,
                       context, exception, **kwargs):
    if exception:
        print(f"Request to {name} failed: {exception}")
    if response.status_code >= 400:
        print(f"Request to {name} failed with status {response.status_code}")
