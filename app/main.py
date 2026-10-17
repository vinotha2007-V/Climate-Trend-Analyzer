"""
Climate Trend Analyzer - FastAPI Application Entry Point.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api.routes_analysis import router as router_analysis
from app.api.routes_datasets import router as router_datasets
from app.api.routes_export import router as router_export

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_HTML = BASE_DIR / "templates" / "index.html"

app = FastAPI(
    title="Climate Trend Analyzer API",
    description="Statistical time-series analysis, moving averages, and anomaly detection for climate observations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register API Routers
app.include_router(router_datasets)
app.include_router(router_analysis)
app.include_router(router_export)


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the single-page climate analytics dashboard."""
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return {"message": "Climate Trend Analyzer Dashboard"}


@app.get("/health", tags=["Health"])
def health_check():
    """Service health verification endpoint."""
    return {
        "status": "healthy",
        "service": "Climate Trend Analyzer",
        "phase": "Phase 6 - Interactive Web Dashboard",
        "version": "1.0.0",
    }
