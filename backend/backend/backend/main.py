"""
WaitWise v2.0 Backend

A predictive human-flow intelligence platform that learns and improves over time.

Features:
- Real-time crowd tracking
- ML-based predictions with self-learning
- Smart recommendations
- User notifications and alerts
- Comprehensive analytics
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import uvicorn

from models import (
    Base,
    Location,
    User,
    UserPreferences,
    CrowdReport,
    Prediction,
    Recommendation,
    Alert,
    UserFeedback,
    ActivityLog,
)

from ml import CrowdPredictionEngine, SelfLearningSystem, run_learning_cycle


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/waitwise"
)

SQLALCHEMY_ECHO = os.getenv(
    "SQLALCHEMY_ECHO",
    "false"
).lower() == "true"


if "postgresql" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        echo=SQLALCHEMY_ECHO,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    engine = create_engine(
        "sqlite:///./waitwise.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=SQLALCHEMY_ECHO
    )


SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CrowdReportRequest(BaseModel):
    location_id: str
    crowd_level: int
    wait_time_minutes: Optional[int] = None
    comment: Optional[str] = None
    confidence: float = 0.5


# ============================================================================
# DATABASE DEPENDENCIES
# ============================================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="WaitWise v2.0",
    description="Predictive human-flow intelligence platform",
    version="2.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():

    logger.info("Starting WaitWise Backend v2.0")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

    with get_db_context() as db:

        location_count = db.query(Location).count()

        if location_count == 0:
            logger.info("Seeding sample locations...")
            _seed_sample_data(db)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down WaitWise Backend")


# ============================================================================
# SAMPLE DATA
# ============================================================================

def _seed_sample_data(db: Session):

    locations = [

        Location(
            name="Central Mall",
            description="Major shopping center",
            category="shopping_mall",
            latitude=40.7128,
            longitude=-74.0060,
            capacity=5000,
            typical_peak_start=18,
            typical_peak_end=21
        ),

        Location(
            name="Burger House",
            description="Popular burger restaurant",
            category="restaurant",
            latitude=40.7150,
            longitude=-74.0050,
            capacity=200,
            typical_peak_start=12,
            typical_peak
