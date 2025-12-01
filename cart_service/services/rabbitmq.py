import json
import asyncio
import os
from typing import Dict, Any
import aio_pika
from aio_pika import ExchangeType
import logging

logger = logging.getLogger(__name__)

class RabbitMQService:
    """RabbitMQ service for publishing order events"""
    
    def __init__(self, rabbitmq_url: str = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        logger.info(f"Initializing RabbitMQ service with URL: {self.rabbitmq_url}")
        self.connection = None
        self.channel = None
        self.exchange = None
        self.exchange_name = "orders_exchange"
        
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Declare exchange for topic-based routing
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,  # Topic exchange for pattern-based routing
                durable=True
            )
            
            logger.info("Connected to RabbitMQ successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")
    
    async def publish_order_event(self, order_data: Dict[str, Any], event_type: str = "order_created"):
        """
        Publish order event to RabbitMQ exchange
        
        Args:
            order_data: Order data dictionary (already serializable)
            event_type: Type of event (default: order_created)
        """
        try:
            # Ensure connection is established
            if not self.connection or self.connection.is_closed:
                await self.connect()
            
            # Create event payload
            event_payload = {
                "event_type": event_type,
                "timestamp": order_data.get("orderDate"),
                "data": order_data
            }
            
            # Serialize to JSON
            message_body = json.dumps(event_payload, default=str)
            
            # Create message
            message = aio_pika.Message(
                message_body.encode('utf-8'),
                content_type='application/json',
                headers={
                    'event_type': event_type,
                    'order_id': order_data.get('orderId'),
                    'customer_id': order_data.get('customerId')
                }
            )
            
            # Publish to exchange with routing key: new.{orderId}
            order_id = order_data.get("orderId")
            routing_key = f"new.{order_id}"
            await self.exchange.publish(message, routing_key=routing_key)
            
            logger.info(f"Published {event_type} event for order {order_data.get('orderId')}")
            
        except Exception as e:
            logger.error(f"Failed to publish order event: {str(e)}")
            # Re-raise the exception so the caller can handle it
            raise

    async def ensure_connection(self):
        """Ensure RabbitMQ connection is active"""
        if not self.connection or self.connection.is_closed:
            await self.connect()

# Global RabbitMQ service instance
rabbitmq_service = RabbitMQService()

async def get_rabbitmq_service() -> RabbitMQService:
    """Dependency function to get RabbitMQ service instance"""
    # Don't force connection here - let the service handle it when publishing
    return rabbitmq_service

# Context manager for connection lifecycle
class RabbitMQConnection:
    """Context manager for RabbitMQ connections"""
    
    def __init__(self, rabbitmq_url: str = None):
        self.service = RabbitMQService(rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672"))
    
    async def __aenter__(self):
        await self.service.connect()
        return self.service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.service.disconnect()