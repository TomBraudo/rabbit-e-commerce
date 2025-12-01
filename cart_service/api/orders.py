from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import logging
import random
import string
import uuid
import re

# Import RabbitMQ service
from services.rabbitmq import get_rabbitmq_service, RabbitMQService

# Set up logging
logger = logging.getLogger(__name__)

# In-memory set to track existing orderIds
existing_order_ids: set[str] = set()

# Create router instance
router = APIRouter(
    prefix="",
    tags=["orders"],
    responses={404: {"description": "Not found"}}
)

# Pydantic models for request/response validation
class CreateOrderRequest(BaseModel):
    """Simplified order creation request model with basic validation"""
    orderId: str = Field(..., description="Unique identifier for the order (must be a string)")
    numberOfItems: int = Field(..., ge=1, description="Number of items to generate (must be an integer greater than or equal to 1)")
    
    # Allow extra fields but ignore them
    model_config = {"extra": "ignore"}

class OrderItem(BaseModel):
    """Order item model"""
    itemId: str = Field(..., description="Unique identifier for the item")
    quantity: int = Field(..., gt=0, description="Quantity of the item (must be greater than 0)")
    price: Decimal = Field(..., description="Price of a single unit of the item")

class OrderResponse(BaseModel):
    """Order response model"""
    orderId: str = Field(..., description="Unique identifier for the order")
    customerId: str = Field(..., description="Unique identifier for the customer")
    orderDate: str = Field(..., description="Timestamp in ISO 8601 format")
    items: List[OrderItem] = Field(..., description="Array of order items")
    totalAmount: Decimal = Field(..., description="Total cost of the order")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    status: str = Field(..., description="Status of the order (e.g., 'pending', 'confirmed')")
    
    class Config:
        from_attributes = True

# Dependency functions
async def get_current_user():
    """Placeholder for user authentication dependency"""
    # TODO: Implement user authentication logic
    pass

async def validate_order_access(order_id: int, user=Depends(get_current_user)):
    """Validate user has access to specific order"""
    # TODO: Implement order access validation
    pass

# Exception handlers will be added to the main FastAPI app
# Note: Exception handlers should be registered on the main app, not the router

# Helper functions
def generate_random_string(length: int = 8) -> str:
    """Generate random string for IDs"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_random_items(count: int) -> List[OrderItem]:
    """Generate random order items"""
    items = []
    for _ in range(count):
        item = OrderItem(
            itemId=generate_random_string(6),
            quantity=random.randint(1, 10),
            price=Decimal(str(round(random.uniform(5.0, 100.0), 2)))
        )
        items.append(item)
    return items

# API Endpoints
@router.post("/create-order", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_request: CreateOrderRequest,
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service)
):
    """Create a new order with randomly generated data and publish to RabbitMQ"""
    # Check if orderId already exists
    if order_request.orderId in existing_order_ids:
        logger.warning(f"Order ID already exists: {order_request.orderId}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order with ID '{order_request.orderId}' already exists"
        )
    
    # Generate random data
    customer_id = f"CUST_{generate_random_string(8)}"
    order_date = datetime.now().isoformat()
    items = generate_random_items(order_request.numberOfItems)
    
    # Calculate total amount
    total_amount = sum(item.price * item.quantity for item in items)
    
    # Random currency and status
    currencies = ["USD", "ILS"]
    statuses = ["new"]
    
    order_response = OrderResponse(
        orderId=order_request.orderId,
        customerId=customer_id,
        orderDate=order_date,
        items=items,
        totalAmount=total_amount,
        currency=random.choice(currencies),
        status=random.choice(statuses)
    )
    
    # Publish order event to RabbitMQ
    try:
        # Convert Pydantic model to dict for JSON serialization
        order_dict = order_response.model_dump()
        await rabbitmq.publish_order_event(order_dict, "order_created")
        logger.info(f"Order event published to RabbitMQ for order: {order_request.orderId}")
        
        # Add orderId to the set after successful publication
        existing_order_ids.add(order_request.orderId)
    except Exception as rabbitmq_error:
        logger.error(f"Failed to publish to RabbitMQ: {str(rabbitmq_error)}")
        # Note: We continue execution even if RabbitMQ fails
        # Still add to set since order was created (RabbitMQ failure is non-critical)
        existing_order_ids.add(order_request.orderId)
    
    logger.info(f"Order created successfully: {order_request.orderId}")
    return order_response
