import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List

from data.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class OrderNotFoundError(Exception):
    """Raised when an order cannot be located in the repository."""


class OrderService:
    """Business logic for processing and retrieving orders."""

    SHIPPING_RATE = Decimal("0.02")

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def handle_order_event(self, event_payload: Dict[str, Any]) -> None:
        """
        Persist eligible orders that arrive via RabbitMQ.
        Only orders whose status is 'new' are tracked.
        """
        order_data = event_payload.get("data", {})
        status = order_data.get("status")

        if status != "new":
            logger.info(
                "Skipping order %s because status is %s",
                order_data.get("orderId"),
                status,
            )
            return

        normalized_items = self._normalize_items(order_data.get("items", []))
        total_amount = self._decimalize(order_data.get("totalAmount"))
        shipping_cost = (total_amount * self.SHIPPING_RATE).quantize(Decimal("0.01"))

        record = {
            "orderId": order_data.get("orderId"),
            "customerId": order_data.get("customerId"),
            "orderDate": order_data.get("orderDate"),
            "items": normalized_items,
            "totalAmount": total_amount,
            "currency": order_data.get("currency"),
            "status": status,
            "shippingCost": shipping_cost,
            "metadata": {
                "eventType": event_payload.get("event_type"),
                "receivedAt": event_payload.get("timestamp"),
            },
        }

        await self._repository.save(record["orderId"], record)
        logger.info(
            "Stored order %s with shipping cost %s",
            record["orderId"],
            record["shippingCost"],
        )

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Return the stored order enriched with shipping info."""
        order = await self._repository.get(order_id)
        if not order:
            raise OrderNotFoundError(f"Order {order_id} was not found")
        return order

    def _normalize_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure quantities and prices are typed consistently."""
        normalized = []
        for item in items:
            price = self._decimalize(item.get("price"))
            quantity = int(item.get("quantity", 0))
            normalized.append(
                {
                    "itemId": item.get("itemId"),
                    "quantity": quantity,
                    "price": price,
                    "lineTotal": (price * Decimal(quantity)).quantize(Decimal("0.01")),
                }
            )
        return normalized

    def _decimalize(self, raw_value: Any) -> Decimal:
        """Convert arbitrary input into a Decimal."""
        if raw_value is None:
            return Decimal("0")
        if isinstance(raw_value, Decimal):
            return raw_value
        try:
            return Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            logger.warning("Failed to convert value %s to Decimal; defaulting to 0", raw_value)
            return Decimal("0")

