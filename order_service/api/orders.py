from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.order_service import OrderService, OrderNotFoundError
from container import order_service as order_service_instance

router = APIRouter(prefix="")


class OrderItemResponse(BaseModel):
    itemId: str
    quantity: int
    price: Decimal
    lineTotal: Decimal


class OrderDetailsResponse(BaseModel):
    orderId: str
    customerId: str
    orderDate: str
    items: List[OrderItemResponse]
    totalAmount: Decimal
    currency: str
    status: str
    shippingCost: Decimal = Field(..., description="Calculated shipping charge")


async def get_order_service() -> OrderService:
    return order_service_instance


@router.get("/order-details", response_model=OrderDetailsResponse)
async def order_details(
    order_id: str = Query(..., alias="orderId", description="Identifier of the order to retrieve"),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Retrieve stored order details including the computed shipping cost.
    """
    try:
        order = await order_service.get_order(order_id)
        return order
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )

