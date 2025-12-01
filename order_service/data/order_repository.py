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
        """Persist or update an order inside the repository."""
        async with self._lock:
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

