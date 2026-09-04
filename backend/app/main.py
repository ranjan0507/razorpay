from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.analytics import run_merchant_analytics
from app.database import SessionLocal, init_db


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
