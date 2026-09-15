"""
PR Lifecycle Tracker & Reconciliation Engine
Tracks PR statuses (PR_CREATED, REVIEW_PENDING, APPROVED, MERGED, CLOSED) and reconciles local DB with live GitHub state.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database.models import PRTracker, AgentRun
from github_mcp import GitHubMCPTools

logger = logging.getLogger(__name__)


class PRLifecycleTracker:
    """Manages PR lifecycle state and reconciles external GitHub changes."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def register_pr(
        self,
        run_id: str,
        repo_name: str,
        pr_number: int,
        title: str,
        branch_name: str,
        url: str = ""
    ) -> PRTracker:
        """Register a newly created PR in the database tracker."""
        tracker_id = f"{repo_name.strip().replace('/', ':')}:{pr_number}"
        
        pr_entry = self.db.query(PRTracker).filter(PRTracker.id == tracker_id).first()
        if not pr_entry:
            pr_entry = PRTracker(
                id=tracker_id,
                run_id=run_id,
                repo_name=repo_name,
                pr_number=pr_number,
                title=title,
                branch_name=branch_name,
                status="PR_CREATED",
                url=url,
                updated_at=time.time()
            )
            self.db.add(pr_entry)
        else:
            pr_entry.title = title
            pr_entry.status = "PR_CREATED"
            pr_entry.url = url
            pr_entry.updated_at = time.time()

        self.db.commit()
        self.db.refresh(pr_entry)
        logger.info(f"[PRTracker] Registered PR #{pr_number} for repo {repo_name} (Run {run_id})")
        return pr_entry

    def update_pr_status(self, repo_name: str, pr_number: int, new_status: str) -> Optional[PRTracker]:
        """Update local status of a PR."""
        tracker_id = f"{repo_name.strip().replace('/', ':')}:{pr_number}"
        pr_entry = self.db.query(PRTracker).filter(PRTracker.id == tracker_id).first()
        if pr_entry:
            pr_entry.status = new_status
            pr_entry.updated_at = time.time()
            self.db.commit()
            self.db.refresh(pr_entry)
            logger.info(f"[PRTracker] Updated PR #{pr_number} status to {new_status}")
        return pr_entry

    def reconcile_with_github(self, mcp_tools: GitHubMCPTools, repo_name: str) -> List[Dict[str, Any]]:
        """
        Reconciliation Job:
        Fetches live PR status from GitHub MCP and updates local database state if divergent.
        """
        trackers = self.db.query(PRTracker).filter(PRTracker.repo_name == repo_name).all()
        reconciled = []

        for tracker in trackers:
            try:
                live_pr = mcp_tools.get_pull_request(repo_name, tracker.pr_number)
                live_state = live_pr.get("state", "").lower()
                
                # Map GitHub state to tracker status
                target_status = tracker.status
                if live_state == "closed":
                    target_status = "CLOSED"
                elif live_state == "open" and tracker.status not in ["CHANGES_REQUESTED", "APPROVED"]:
                    target_status = "REVIEW_PENDING"

                if tracker.status != target_status:
                    old_status = tracker.status
                    tracker.status = target_status
                    tracker.updated_at = time.time()
                    self.db.commit()
                    reconciled.append({
                        "pr_number": tracker.pr_number,
                        "old_status": old_status,
                        "new_status": target_status
                    })
                    logger.info(f"[PRTracker] Reconciled PR #{tracker.pr_number}: {old_status} -> {target_status}")
            except Exception as e:
                logger.warning(f"[PRTracker] Reconciliation check failed for PR #{tracker.pr_number}: {e}")

        return reconciled
