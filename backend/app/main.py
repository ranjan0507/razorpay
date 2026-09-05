from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from app.analytics import run_merchant_analytics
from app.ai import (
    generate_risk_explanation,
    answer_risk_question,
    RiskExplanationResponse,
    RiskQAResponse,
)
from app.database import SessionLocal, init_db


class RiskQARequest(BaseModel):
    question: str = Field(..., description="Merchant question about chargeback risk analytics")

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace only")
        return v.strip()


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



# Mount compiled frontend dist if directory exists
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
