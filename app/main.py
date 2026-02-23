"""
URL Shortener FastAPI Application Entry Point

This module initializes and configures the FastAPI application, including:
- Database connection and session management
- Redis cache initialization
- Middleware setup (CORS, error handling)
- Application lifespan management (startup/shutdown)
- Server configuration and startup

The application serves as the main entry point for the URL shortening service.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import settings
from app.models import init_db
from app.routes import router
from app.cache import get_cache

# ==================== LOGGING CONFIGURATION ====================
# Setup centralized logging with timestamp, level, and message
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DATABASE INITIALIZATION ====================
# Initialize database engine and session factory
# This creates the connection pool and creates all tables if needed
engine, SessionLocal = init_db(settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup/shutdown events.
    
    Startup: Initializes services and logs configuration
    Shutdown: Cleans up database connections
    
    Yields:
        None - This context manager yields during app runtime
    """
    # ==================== STARTUP ====================
    logger.info("Starting URL Shortener Service")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
    
    # Initialize cache and log connection status
    cache = get_cache()
    if cache.is_connected():
        logger.info("Redis cache connected successfully")
        cache_info = cache.get_stats_info()
        logger.info(f"Cache stats: {cache_info}")
    else:
        logger.warning("Redis cache unavailable - running in degraded mode (no caching)")
    
    # Yield control to FastAPI - app runs here
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("Shutting down URL Shortener Service")
    engine.dispose()  # Close all database connections


# ==================== FASTAPI APP CREATION ====================
# Create FastAPI application with custom lifespan management
app = FastAPI(
    title="URL Shortener Service",
    description="Scalable URL shortening service with Redis caching and analytics",
    version="1.0.0",
    lifespan=lifespan
)

# ==================== MIDDLEWARE SETUP ====================
# CORS middleware - enable cross-origin requests (configure as needed for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== EXCEPTION HANDLERS ====================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI validation errors with detailed error messages.
    
    Returns detailed information about validation failures to help clients
    fix their requests (e.g., invalid URL format, missing required fields).
    
    Args:
        request: The HTTP request that failed validation
        exc: The validation error containing error details
        
    Returns:
        JSONResponse with status 422 and error details
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected application errors.
    
    Logs the error and returns a generic error response to avoid
    leaking sensitive information to clients.
    
    Args:
        request: The HTTP request that caused the error
        exc: The unexpected exception
        
    Returns:
        JSONResponse with status 500 and generic error message
    """
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# ==================== ROUTE REGISTRATION ====================
# Include all API routes from routes module
app.include_router(router)


# ==================== ENDPOINT DEFINITIONS ====================
@app.get("/")
async def root():
    """
    Root endpoint providing API information.
    
    Returns:
        dict with service info, version, and documentation links
    """
    return {
        "service": "URL Shortener",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": "/api/v1"
    }


# Additional endpoints
@app.get("/api/v1/health")
async def health():
    """Health check endpoint."""
    from routes import health_check
    return await health_check(None)


@app.get("/api/v1/stats")
async def service_stats():
    """Service statistics endpoint."""
    from routes import get_service_stats
    from models import get_db_session, SessionLocal
    db = SessionLocal()
    try:
        return await get_service_stats(db)
    finally:
        db.close()


def main():
    """Main entry point for the application."""
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
