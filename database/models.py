"""
SQLAlchemy Relational Database Models
Defines schema for Users, Repositories, Agent Runs, Steps, Approvals, Evaluations, Webhook Events, and Audit Logs.
"""
import time
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(Float, default=time.time)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="user", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)  # owner/repo
    default_branch = Column(String, default="main")
    created_at = Column(Float, default=time.time)

    owner = relationship("User", back_populates="repositories")
    memory = relationship("RepositoryMemory", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    runs = relationship("AgentRun", back_populates="repository", cascade="all, delete-orphan")


class RepositoryMemory(Base):
    __tablename__ = "repository_memories"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True, index=True)
    facts_json = Column(JSON, default=dict)
    architecture_json = Column(JSON, default=dict)
    conventions_json = Column(JSON, default=dict)
    history_json = Column(JSON, default=dict)
    updated_at = Column(Float, default=time.time)

    repository = relationship("Repository", back_populates="memory")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, index=True)  # RUN-XXXXXX
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    user_request = Column(Text, nullable=False)
    status = Column(String, default="QUEUED", index=True)  # QUEUED, RUNNING, WAITING_FOR_APPROVAL, COMPLETED, FAILED, CANCELLED
    workflow_type = Column(String, default="REPO_INTELLIGENCE")
    branch_name = Column(String, default="")
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)
    duration_sec = Column(Float, default=0.0)

    user = relationship("User", back_populates="agent_runs")
    repository = relationship("Repository", back_populates="runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")
    approval = relationship("Approval", back_populates="run", uselist=False, cascade="all, delete-orphan")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    agent_name = Column(String, nullable=False)
    action = Column(Text, nullable=False)
    tool_name = Column(String, nullable=True)
    duration_sec = Column(Float, default=0.0)
    status = Column(String, default="SUCCESS")
    timestamp = Column(Float, default=time.time)

    run = relationship("AgentRun", back_populates="steps")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    repo_name = Column(String, nullable=False)
    target_branch = Column(String, nullable=False)
    change_summary = Column(Text, nullable=False)
    status = Column(String, default="PENDING", index=True)  # PENDING, APPROVED, REJECTED
    payload_json = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time)

    run = relationship("AgentRun", back_populates="approval")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pass_rate_pct = Column(Float, default=0.0)
    routing_accuracy_pct = Column(Float, default=0.0)
    avg_latency_sec = Column(Float, default=0.0)
    created_at = Column(Float, default=time.time)

    results = relationship("EvaluationResult", back_populates="eval_run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    eval_run_id = Column(String, ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    test_id = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    passed = Column(Boolean, default=False)
    latency_sec = Column(Float, default=0.0)

    eval_run = relationship("EvaluationRun", back_populates="results")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    repository_name = Column(String, nullable=False, index=True)
    payload_json = Column(JSON, default=dict)
    processed = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    resource = Column(String, nullable=False)
    status = Column(String, default="SUCCESS")
    timestamp = Column(Float, default=time.time)


class AgentCheckpoint(Base):
    __tablename__ = "agent_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    step_name = Column(String, nullable=False, index=True)
    status = Column(String, default="COMPLETED")
    state_json = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time)


class PRTracker(Base):
    __tablename__ = "pr_trackers"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=True, index=True)
    repo_name = Column(String, nullable=False, index=True)
    pr_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    branch_name = Column(String, nullable=False)
    status = Column(String, default="PR_CREATED", index=True)  # PR_CREATED, PR_UPDATED, REVIEW_PENDING, CHANGES_REQUESTED, APPROVED, MERGED, CLOSED
    url = Column(String, default="")
    updated_at = Column(Float, default=time.time)


class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    error_code = Column(String, nullable=False)
    last_error = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0)
    payload_json = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time)


class CodeEntityModel(Base):
    __tablename__ = "code_entities"

    id = Column(String, primary_key=True, index=True)  # repo:path:symbol
    repository_name = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # module, class, function, test, config
    name = Column(String, nullable=False, index=True)
    qualified_name = Column(String, nullable=False)
    signature = Column(String, default="")
    start_line = Column(Integer, default=1)
    end_line = Column(Integer, default=1)
    metadata_json = Column(JSON, default=dict)


class CodeRelationshipModel(Base):
    __tablename__ = "code_relationships"

    id = Column(Integer, primary_key=True, index=True)
    repository_name = Column(String, nullable=False, index=True)
    source_entity_id = Column(String, nullable=False, index=True)
    target_entity_id = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)  # imports, calls, inherits, tested_by, depends_on


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="LOW", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    reasons_json = Column(JSON, default=list)
    created_at = Column(Float, default=time.time)


class PatchQualityAssessmentModel(Base):
    __tablename__ = "patch_quality_assessments"

    id = Column(String, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)
    quality_score = Column(Float, default=0.0)
    metrics_json = Column(JSON, default=dict)
    recommendations_json = Column(JSON, default=list)
    created_at = Column(Float, default=time.time)


class IssueSimilarityModel(Base):
    __tablename__ = "issue_similarities"

    id = Column(String, primary_key=True, index=True)
    repo_name = Column(String, nullable=False, index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    duplicate_issue_number = Column(Integer, nullable=False)
    similarity_score = Column(Float, default=0.0)
    evidence_json = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time)


class EngineeringTaskModel(Base):
    __tablename__ = "engineering_tasks"

    id = Column(String, primary_key=True, index=True)  # TASK-XXXXXX
    tenant_id = Column(Integer, nullable=False, index=True)
    repository_name = Column(String, nullable=False, index=True)
    objective = Column(Text, nullable=False)
    status = Column(String, default="INTAKE", index=True)
    autonomy_level = Column(Integer, default=2)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class TaskCriterionModel(Base):
    __tablename__ = "task_criteria"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("engineering_tasks.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(String, default="UNKNOWN", index=True)  # PASS, FAIL, UNKNOWN, NOT_APPLICABLE
    evidence_json = Column(JSON, default=dict)


class FeedbackEventModel(Base):
    __tablename__ = "feedback_events"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # CI_FAILURE, PR_REVIEW, MERGE_CONFLICT
    payload_json = Column(JSON, default=dict)
    created_at = Column(Float, default=time.time)


class RootCauseAnalysisModel(Base):
    __tablename__ = "root_cause_analyses"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    failure_summary = Column(Text, nullable=False)
    hypotheses_json = Column(JSON, default=list)
    confidence = Column(String, default="HIGH")
    created_at = Column(Float, default=time.time)


class EngineeringOutcomeModel(Base):
    __tablename__ = "engineering_outcomes"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)
    patch_quality_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    outcome_status = Column(String, default="SUCCESS", index=True)
    created_at = Column(Float, default=time.time)


class AutonomyDecisionModel(Base):
    __tablename__ = "autonomy_decisions"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    decision = Column(String, nullable=False, index=True)  # SAFE_TO_PROCEED, REQUIRES_APPROVAL, BLOCKED
    reasons_json = Column(JSON, default=list)
    created_at = Column(Float, default=time.time)



