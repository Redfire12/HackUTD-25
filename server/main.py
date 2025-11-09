from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from database import engine, Base
from routes import auth, feedback
from services.openai_service import validate_openai_key

# ------------------------------------------------
# Setup and config
# ------------------------------------------------
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

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

# Logging setup
LOG_FILE = "server.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} [{duration:.3f}s]")
    return response

# Validate OpenAI key on startup
if validate_openai_key():
    logger.info("OpenAI API key validated successfully")
else:
    logger.warning("OpenAI API key not configured. AI features will use fallbacks.")

# ------------------------------------------------
# Include routers
# ------------------------------------------------
app.include_router(auth.router)
app.include_router(feedback.router)

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
