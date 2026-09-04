from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db


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
