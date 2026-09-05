from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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


# Mount compiled frontend dist if directory exists
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
