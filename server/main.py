from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

# ------------------------------------------------
# Setup and config
# ------------------------------------------------
load_dotenv() 

# Logging setup (must be early for error handling)
LOG_FILE = os.getenv("LOG_FILE", "")
if LOG_FILE:
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

logger = logging.getLogger(__name__)

# Database setup
from database import engine, Base, ensure_feedback_table_columns

# Create database tables
Base.metadata.create_all(bind=engine)
ensure_feedback_table_columns()

# Initialize FastAPI app
app = FastAPI(
    title="HackUTD Customer Feedback Dashboard API",
    version="2.0.0",
    description="API for analyzing customer feedback with AI-powered insights"
)

# ------------------------------------------------
# CORS configuration
# ------------------------------------------------
default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
if cors_origins_env:
    allow_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    if not allow_origins:
        allow_origins = default_origins
else:
    allow_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes (must be after app creation for dependency injection)
from routes import auth, feedback

# Import Hugging Face service gracefully - don't fail if it has issues
try:
    from services.huggingface_service import validate_huggingface_key
    HF_SERVICE_AVAILABLE = True
except Exception as e:
    HF_SERVICE_AVAILABLE = False
    logger.warning(f"Could not import Hugging Face service: {e}. AI features will use fallbacks.")
    def validate_huggingface_key():
        return False

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} [{duration:.3f}s]")
    return response

# ------------------------------------------------
# Include routers (CRITICAL: Must be registered before validation)
# ------------------------------------------------
app.include_router(auth.router)
app.include_router(feedback.router)

# Validate Hugging Face API on startup (non-blocking, after routes are registered)
# This ensures auth routes are always available even if AI service fails
if HF_SERVICE_AVAILABLE:
    try:
        if validate_huggingface_key():
            logger.info("Hugging Face API validated successfully")
        else:
            logger.warning("Hugging Face API not configured. AI features will use fallbacks.")
    except Exception as e:
        logger.warning(f"Hugging Face API validation failed: {e}. AI features will use fallbacks.")
else:
    logger.warning("Hugging Face service not available. AI features will use fallbacks.")

# ------------------------------------------------
# Root route
# ------------------------------------------------
@app.get("/")
def root():
    """Root endpoint to check API status."""
    return {
        "status": "ok",
        "message": "HackUTD Customer Feedback Dashboard API is running",
        "version": "2.0.0",
        "docs": "/docs"
    }

# ------------------------------------------------
# Health check
# ------------------------------------------------
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}
