"""
Retry Handler & Exponential Backoff Policy
Handles transient error classification and resilient retry execution with backoff and jitter.
"""
import time
import random
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)

# Non-retryable error keywords
NON_RETRYABLE_PATTERNS = [
    "invalid authentication",
    "unauthorized",
    "permission denied",
    "prompt injection detected",
    "repository not found",
    "schema validation failed",
    "idempotency key mismatch",
    "policy violation",
    "approval rejected"
]


def is_transient_error(error: Exception) -> bool:
    """Classify whether an exception is transient (network timeout, rate limit, temporary disconnect)."""
    err_str = str(error).lower()
    for pattern in NON_RETRYABLE_PATTERNS:
        if pattern in err_str:
            return False
    return True


def execute_with_retry(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    **kwargs
) -> Any:
    """
    Executes a function with exponential backoff + jitter retry strategy.
    """
    attempt = 0
    delay = initial_delay

    while True:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            attempt += 1
            transient = is_transient_error(exc)

            if not transient:
                logger.error(f"[RetryHandler] Non-transient error encountered: {exc}. Retries aborted.")
                raise exc

            if attempt > max_retries:
                logger.error(f"[RetryHandler] Exhausted max retries ({max_retries}). Last error: {exc}")
                raise exc

            # Add jitter to delay
            jitter = random.uniform(0, 0.1 * delay)
            sleep_time = delay + jitter
            logger.warning(f"[RetryHandler] Attempt {attempt}/{max_retries} failed ({exc}). Retrying in {sleep_time:.2f}s...")
            time.sleep(sleep_time)
            delay *= backoff_factor
