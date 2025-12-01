from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import status, Request
import logging
import uvicorn
from contextlib import asynccontextmanager

# Import your API routers
from api.orders import router as orders_router
from services.rabbitmq import rabbitmq_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting up the application...")
    try:
        # Initialize RabbitMQ connection
        await rabbitmq_service.connect()
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ during startup: {e}")
        # Continue without RabbitMQ - the service will attempt to reconnect when needed
    
    yield
    
    # Shutdown
    logger.info("Shutting down the application...")
    try:
        # Clean up RabbitMQ connection
        await rabbitmq_service.disconnect()
        logger.info("RabbitMQ connection closed")
    except Exception as e:
        logger.error(f"Error during RabbitMQ cleanup: {e}")

# Create FastAPI application
app = FastAPI(
    title="Orders API",
    description="API for managing orders with RabbitMQ event publishing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orders_router, tags=["orders"])

# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": str(exc)}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Cart Service",
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to the Cart Service",
        "docs": "/docs",
        "health": "/health",
    }

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
