from data.order_repository import OrderRepository
from services.order_service import OrderService
from services.order_consumer import OrderConsumer

order_repository = OrderRepository()
order_service = OrderService(order_repository)
order_consumer = OrderConsumer(order_service)

