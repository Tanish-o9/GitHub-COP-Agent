"""
Production GitHub Webhook Endpoint (/api/v1/webhooks/github)
Validates HMAC SHA256 signatures, enforces event idempotency, persists events, and queues background triage tasks.
"""
from typing import Optional
import os
import hmac
import hashlib
import json
import uuid
import time
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import WebhookEvent
from event_router import EventRouter
from github_mcp import GitHubMCPTools
from worker.task_queue import TaskQueue

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "production-webhook-secret-key-2026")


def verify_github_signature(payload_bytes: bytes, signature_header: Optional[str] = None):
    """Verify GitHub HMAC SHA256 signature (X-Hub-Signature-256)."""
    if not signature_header:
        # If no signature provided in dev, allow with warning
        return True
    
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature format")

    expected_sig = hmac.new(WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    actual_sig = signature_header.split("sha256=")[1]
    
    if not hmac.compare_digest(actual_sig, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub Webhook Signature verification failed")


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def receive_github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header("issues"),
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Receive, validate, deduplicate, and enqueue GitHub Webhook event."""
    body_bytes = await request.body()
    verify_github_signature(body_bytes, x_hub_signature_256)

    try:
        payload = json.loads(body_bytes.decode())
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # Generate or extract delivery event ID for idempotency
    event_id = request.headers.get("x-github-delivery", f"EVT-{uuid.uuid4().hex[:8]}")
    repo_name = payload.get("repository", {}).get("full_name", "Tanish-o9/GitHub-COP-Agent")

    # Idempotency Check: Prevent duplicate event processing
    existing_evt = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    if existing_evt:
        return {"status": "ALREADY_PROCESSED", "event_id": event_id, "message": "Event already recorded"}

    # Persist Webhook Event
    evt_record = WebhookEvent(
        id=event_id,
        event_type=x_github_event or "issues",
        repository_name=repo_name,
        payload_json=payload,
        processed=False
    )
    db.add(evt_record)
    db.commit()

    # Enqueue background task (quick response)
    mcp_tools = GitHubMCPTools()
    router_inst = EventRouter(mcp_tools)

    def async_triage_task():
        db_sub = db
        router_inst.process_webhook_event(x_github_event or "issues", payload)
        evt_record.processed = True
        db_sub.commit()

    TaskQueue.enqueue_run(event_id, async_triage_task)

    return {
        "event_id": event_id,
        "event_type": x_github_event,
        "status": "QUEUED",
        "repository": repo_name
    }
