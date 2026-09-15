"""
Task Queue & Distributed Lock Manager Module
Handles Redis task queueing, distributed locking for same-run operations, and in-memory background worker fallback.
"""
import os
import time
import uuid
import threading
from typing import Dict, Any, Optional, Callable

try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    HAS_REDIS = True
except Exception:
    redis_client = None
    HAS_REDIS = False


def get_redis_client():
    """Retrieve Redis client instance or None if Redis is unreachable."""
    return redis_client if HAS_REDIS else None


class DistributedLock:
    """
    Redis-backed or threading-backed distributed lock manager.
    """

    _local_locks: Dict[str, threading.Lock] = {}

    @classmethod
    def acquire_lock(cls, resource_name: str, timeout_sec: int = 30) -> bool:
        """Acquire lock for critical operations (e.g. branch creation)."""
        if HAS_REDIS and redis_client:
            try:
                return bool(redis_client.set(f"lock:{resource_name}", "1", nx=True, ex=timeout_sec))
            except Exception:
                pass

        if resource_name not in cls._local_locks:
            cls._local_locks[resource_name] = threading.Lock()
        return cls._local_locks[resource_name].acquire(blocking=False)

    @classmethod
    def release_lock(cls, resource_name: str):
        """Release lock after operation completes."""
        if HAS_REDIS and redis_client:
            try:
                redis_client.delete(f"lock:{resource_name}")
                return
            except Exception:
                pass

        if resource_name in cls._local_locks:
            try:
                cls._local_locks[resource_name].release()
            except RuntimeError:
                pass


class TaskQueue:
    """
    Enqueues async agent workflow runs.
    """

    @classmethod
    def enqueue_run(cls, run_id: str, task_func: Callable, *args, **kwargs):
        """Enqueue workflow task to background execution thread."""
        t = threading.Thread(target=task_func, args=args, kwargs=kwargs, daemon=True)
        t.start()
        return run_id
