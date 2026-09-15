"""
Feedback Ingestion Engine
Consumes CI test failures, PR review comments, and merge conflict events, classifying feedback and mapping to task revisions.
"""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Feedback Categories
FEEDBACK_CI_FAILURE = "CI_FAILURE"
FEEDBACK_REVIEW_COMMENT = "REVIEW_COMMENT"
FEEDBACK_MERGE_CONFLICT = "MERGE_CONFLICT"
FEEDBACK_SECURITY_ALERT = "SECURITY_ALERT"
FEEDBACK_UNKNOWN = "UNKNOWN"


@dataclass
class FeedbackItem:
    """Represents a classified feedback event."""
    id: str
    task_id: str
    feedback_type: str  # CI_FAILURE, REVIEW_COMMENT, MERGE_CONFLICT, SECURITY_ALERT
    raw_content: str
    target_file: str = ""
    target_symbol: str = ""
    actionable_summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeedbackEngine:
    """Ingests and classifies continuous engineering feedback from CI and GitHub webhooks."""

    def process_feedback(self, task_id: str, payload: Dict[str, Any]) -> FeedbackItem:
        raw_text = str(payload.get("text", payload.get("body", "")))
        event_type = payload.get("event_type", "").upper()

        # Classify event
        fb_type = FEEDBACK_UNKNOWN
        if "test" in raw_text.lower() or "assertionerror" in raw_text.lower() or "ci" in event_type.lower():
            fb_type = FEEDBACK_CI_FAILURE
        elif "conflict" in raw_text.lower() or "merge" in event_type.lower():
            fb_type = FEEDBACK_MERGE_CONFLICT
        elif "security" in raw_text.lower() or "secret" in raw_text.lower():
            fb_type = FEEDBACK_SECURITY_ALERT
        elif "comment" in event_type.lower() or "review" in event_type.lower():
            fb_type = FEEDBACK_REVIEW_COMMENT

        # Extract target file reference if present
        target_file = ""
        for line in raw_text.splitlines():
            if ".py" in line:
                for part in line.split():
                    if part.endswith(".py"):
                        target_file = part.strip(":'\",")
                        break

        summary = f"Processed {fb_type} feedback for task {task_id}."
        if target_file:
            summary += f" Target file: {target_file}"

        item = FeedbackItem(
            id=f"FB-{int(time.time()*1000)}",
            task_id=task_id,
            feedback_type=fb_type,
            raw_content=raw_text,
            target_file=target_file,
            actionable_summary=summary,
            timestamp=time.time()
        )
        logger.info(f"[FeedbackEngine] Ingested {fb_type} for task {task_id}")
        return item
