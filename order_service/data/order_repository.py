import asyncio
import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class OrderRepository:
    """Simple in-memory repository for storing processed orders."""

    def __init__(self) -> None:
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def save(self, order_id: str, order_data: Dict[str, Any]) -> None:
        """Persist a new order inside the repository.

        If an order with the same ID already exists, the call is a no-op.
        This allows the consumer to simply ack duplicate messages without
        mutating existing state.
        """
        async with self._lock:
            if order_id in self._orders:
                logger.info("Duplicate order %s detected, skipping save", order_id)
                return

            self._orders[order_id] = order_data

        print(f"Order {order_id} saved successfully")
        logger.info("Order %s saved successfully", order_id)

    async def get(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a previously stored order."""
        async with self._lock:
            return self._orders.get(order_id)

    async def clear(self) -> None:
        """Utility helper for tests to reset the repository."""
        async with self._lock:
            self._orders.clear()

