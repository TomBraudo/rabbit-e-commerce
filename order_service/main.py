import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.orders import router as orders_router
from container import order_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the RabbitMQ consumer runs alongside the API."""
    logger.info("Starting Order Service application")
    try:
        await order_consumer.start()
        logger.info("Order consumer is listening for events")
    except Exception as exc:
        logger.exception("Failed to start order consumer: %s", exc)

    yield

    logger.info("Shutting down Order Service application")
    try:
        await order_consumer.stop()
    except Exception as exc:
        logger.exception("Failed to stop order consumer cleanly: %s", exc)


app = FastAPI(
    title="Order Service",
    description="Consumes order events and exposes enriched order details",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(orders_router, tags=["orders"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Order Service"}


@app.get("/")
async def root():
    return {"message": "Order Service is running", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8100, reload=True)

