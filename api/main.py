"""
FastAPI Application Entry Point
Configures CORS, database initialization, API routers, WebSocket endpoints, and health diagnostic checks.
"""
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from database.connection import init_db, get_db
from health_check import HealthCheckManager
from api.routes_auth import router as auth_router
from api.routes_repos import router as repos_router
from api.routes_runs import router as runs_router
from api.routes_approvals import router as approvals_router
from api.routes_evals import router as evals_router
from api.routes_webhooks import router as webhooks_router
from api.routes_ops import router as ops_router
from api.routes_intelligence import router as intelligence_router
from api.routes_engineering import router as engineering_router
from api.websocket import ws_manager

app = FastAPI(
    title="GitHub Cop Agent API",
    description="Production-grade API for multi-user multi-agent repository intelligence, issue analysis, PR reviews, and automated PR creation.",
    version="8.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Initialize Database Tables
@app.on_event("startup")
def on_startup():
    init_db()

# Mount API Routers under /api/v1
app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(runs_router)
app.include_router(approvals_router)
app.include_router(evals_router)
app.include_router(webhooks_router)
app.include_router(ops_router)
app.include_router(intelligence_router)
app.include_router(engineering_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Application Health Status Endpoint."""
    return HealthCheckManager.run_health_check()


@app.get("/ready", tags=["Health"])
def readiness_check():
    """Readiness Check Endpoint for Docker & Load Balancers."""
    return {"status": "READY", "timestamp": time.time()}


@app.websocket("/api/v1/ws/runs/{run_id}")
async def websocket_run_telemetry(websocket: WebSocket, run_id: str):
    """Real-Time WebSocket Progress Telemetry Endpoint."""
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            # Keepalive loop
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
