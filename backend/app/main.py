from datetime import datetime
from typing import List
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from app.analytics import run_merchant_analytics, evaluate_intervention
from app.ai import (
    generate_risk_explanation,
    answer_risk_question,
    generate_intervention_explanation,
    RiskExplanationResponse,
    RiskQAResponse,
    InterventionExplanationResponse,
)
from app.database import SessionLocal, init_db
from app.models import Merchant, Intervention


class RiskQARequest(BaseModel):
    question: str = Field(..., description="Merchant question about chargeback risk analytics")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only")
        return v.strip()


class InterventionCreateRequest(BaseModel):
    action_description: str = Field(..., description="Description of the action taken by the merchant")
    start_date: datetime = Field(..., description="Date when the intervention began")
    target_segment: str = Field(..., description="Target segment for the intervention")
    status: str = Field(..., description="Current status of the intervention")

    @field_validator("action_description", "target_segment", "status")
    @classmethod
    def validate_non_empty_str(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace only")
        return v.strip()


class InterventionResponse(BaseModel):
    id: int
    merchant_id: int
    action_description: str
    start_date: datetime
    target_segment: str
    status: str

    model_config = {"from_attributes": True}



def get_db():
    """Yield a database session per request and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables automatically upon FastAPI app startup
    init_db()
    yield


app = FastAPI(
    title="DisputeGuard API",
    description="AI-powered chargeback risk early-warning system backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for local frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/merchants/{merchant_id}/analytics")
def get_merchant_analytics_endpoint(
    merchant_id: int, db: Session = Depends(get_db)
):
    """Expose completed deterministic analytics pipeline for a merchant."""
    result = run_merchant_analytics(db, merchant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@app.get(
    "/merchants/{merchant_id}/explanation",
    response_model=RiskExplanationResponse,
)
def get_merchant_explanation_endpoint(
    merchant_id: int, db: Session = Depends(get_db)
):
    """Expose Gemini AI risk explanation layer for a merchant."""
    analytics_result = run_merchant_analytics(db, merchant_id)
    if analytics_result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    explanation = generate_risk_explanation(analytics_result)
    return explanation


@app.post(
    "/merchants/{merchant_id}/ask",
    response_model=RiskQAResponse,
)
def ask_merchant_question_endpoint(
    merchant_id: int,
    request: RiskQARequest,
    db: Session = Depends(get_db),
):
    """Expose Gemini AI grounded Q&A layer for a merchant."""
    analytics_result = run_merchant_analytics(db, merchant_id)
    if analytics_result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    qa_response = answer_risk_question(analytics_result, request.question)
    return qa_response


@app.post(
    "/merchants/{merchant_id}/interventions",
    response_model=InterventionResponse,
    status_code=201,
)
def create_merchant_intervention_endpoint(
    merchant_id: int,
    request: InterventionCreateRequest,
    db: Session = Depends(get_db),
):
    """Record a merchant intervention action in the database."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    intervention = Intervention(
        merchant_id=merchant_id,
        action_description=request.action_description,
        start_date=request.start_date,
        target_segment=request.target_segment,
        status=request.status,
    )
    db.add(intervention)
    db.commit()
    db.refresh(intervention)

    return intervention


@app.get(
    "/merchants/{merchant_id}/interventions",
    response_model=List[InterventionResponse],
)
def get_merchant_interventions_endpoint(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve all recorded interventions for a merchant ordered by start_date descending."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    interventions = (
        db.query(Intervention)
        .filter(Intervention.merchant_id == merchant_id)
        .order_by(Intervention.start_date.desc())
        .all()
    )
    return interventions


@app.get("/merchants/{merchant_id}/interventions/{intervention_id}/evaluation")
def get_merchant_intervention_evaluation_endpoint(
    merchant_id: int,
    intervention_id: int,
    db: Session = Depends(get_db),
):
    """Expose deterministic before/after evaluation for a recorded merchant intervention."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if intervention.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Intervention not found for this merchant")

    evaluation = evaluate_intervention(db, intervention_id=intervention_id, window_days=14)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    return evaluation


@app.get(
    "/merchants/{merchant_id}/interventions/{intervention_id}/explanation",
    response_model=InterventionExplanationResponse,
)
def get_merchant_intervention_explanation_endpoint(
    merchant_id: int,
    intervention_id: int,
    db: Session = Depends(get_db),
):
    """Expose Gemini AI explanation for a recorded merchant intervention evaluation."""
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    intervention = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if intervention.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Intervention not found for this merchant")

    evaluation = evaluate_intervention(db, intervention_id=intervention_id, window_days=14)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    explanation = generate_intervention_explanation(evaluation)
    return explanation




# Mount compiled frontend dist if directory exists
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
