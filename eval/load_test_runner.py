"""
Load Testing Benchmark Runner — Phase 6
Simulates concurrent agent requests and measures API throughput, latency percentiles, queue depth, and error rates.
"""
import os
import sys
import time
import concurrent.futures
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import SessionLocal
from database.models import AgentRun, User
from scheduler import ResourceScheduler


class LoadTestRunner:
    """Simulates multi-user concurrent workload and collects real performance metrics."""

    def __init__(self, target_concurrency: int = 10, total_requests: int = 25):
        self.concurrency = target_concurrency
        self.total_requests = total_requests

    def _simulated_request_worker(self, request_id: int) -> Dict[str, Any]:
        """Simulates an API request creation and scheduler check."""
        t0 = time.time()
        db = SessionLocal()
        error = None
        status_code = 200
        try:
            scheduler = ResourceScheduler(db)
            can_run = scheduler.can_start_run(user_id=1, workflow_type="REPO_INTELLIGENCE")
            # Create a lightweight test run
            run = AgentRun(
                id=f"LOAD-{request_id}-{int(time.time()*1000)}",
                user_id=1,
                user_request=f"Load test request #{request_id}",
                status="RUNNING" if can_run else "QUEUED",
                workflow_type="REPO_INTELLIGENCE"
            )
            db.add(run)
            db.commit()
            db.close()
        except Exception as e:
            error = str(e)
            status_code = 500
            try:
                db.close()
            except Exception:
                pass

        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "request_id": request_id,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "error": error
        }

    def run_load_test(self) -> Dict[str, Any]:
        """Executes concurrent load test across thread pool."""
        t_start = time.time()
        results: List[Dict[str, Any]] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [
                executor.submit(self._simulated_request_worker, req_id)
                for req_id in range(1, self.total_requests + 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        total_duration = time.time() - t_start
        latencies = [r["latency_ms"] for r in results]
        errors = [r for r in results if r["error"] is not None]

        latencies.sort()
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        p95_index = int(0.95 * len(latencies))
        p95_latency = latencies[p95_index] if latencies else 0.0
        req_per_sec = round(self.total_requests / total_duration, 2) if total_duration > 0 else 0.0
        error_rate = round((len(errors) / self.total_requests) * 100, 2)

        return {
            "concurrency_level": self.concurrency,
            "total_requests": self.total_requests,
            "total_duration_sec": round(total_duration, 3),
            "requests_per_sec": req_per_sec,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "error_count": len(errors),
            "error_rate_pct": error_rate
        }


if __name__ == "__main__":
    runner = LoadTestRunner(target_concurrency=10, total_requests=25)
    metrics = runner.run_load_test()
    print("LOAD TEST BENCHMARK RESULTS:")
    print(metrics)
