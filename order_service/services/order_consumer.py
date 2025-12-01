import asyncio
import json
import logging
import os
from typing import Optional

import aio_pika
from aio_pika import IncomingMessage

from services.order_service import OrderService

logger = logging.getLogger(__name__)


class OrderConsumer:
    """Consumes RabbitMQ events and delegates them to the order service."""

    def __init__(self, order_service: OrderService, rabbitmq_url: Optional[str] = None) -> None:
        self._order_service = order_service
        self._rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._queue: Optional[aio_pika.Queue] = None
        self._consume_task: Optional[asyncio.Task] = None
        self._exchange_name = "orders_exchange"
        self._queue_name = os.getenv("ORDER_QUEUE_NAME", "order_service_new_orders")

    async def start(self) -> None:
        """Initialize RabbitMQ structures and begin consuming messages."""
        if self._consume_task and not self._consume_task.done():
            return

        await self._connect()
        self._consume_task = asyncio.create_task(self._consume_loop())
        logger.info("Order consumer started")

    async def stop(self) -> None:
        """Stop consuming and teardown the connection."""
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
            finally:
                self._consume_task = None

        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Order consumer connection closed")

    async def _connect(self) -> None:
        """Ensure we have an active connection, channel, queue and binding."""
        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)
        self._channel = await self._connection.channel()

        # Get reference to existing exchange (declared on producer side)
        exchange = await self._channel.get_exchange(self._exchange_name)

        self._queue = await self._channel.declare_queue(
            self._queue_name,
            durable=True,
        )
        # Bind queue with topic pattern "new.*"
        await self._queue.bind(exchange, routing_key="new.*")

    async def _consume_loop(self) -> None:
        """Continuously read messages from the queue."""
        assert self._queue is not None

        try:
            async with self._queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("Order consumer cancelled")
        except Exception as exc:
            logger.exception("Order consumer crashed: %s", exc)

    async def _handle_message(self, message: IncomingMessage) -> None:
        """Parse and process a single message."""
        async with message.process(ignore_processed=True):
            try:
                payload = json.loads(message.body.decode("utf-8"))
            except json.JSONDecodeError:
                logger.error("Received invalid JSON payload")
                return

            order_status = payload.get("data", {}).get("status")
            if order_status != "new":
                logger.info(
                    "Discarding order %s with status %s",
                    payload.get("data", {}).get("orderId"),
                    order_status,
                )
                return

            await self._order_service.handle_order_event(payload)

