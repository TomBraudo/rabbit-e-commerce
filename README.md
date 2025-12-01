# Order and Cart Services Overview

## 1.1 Team Member
- Full name: Tom Braudo
- ID number: 324182914
## 1.2 Team Member
- Full name: Dan Toledano
- ID number: 

## 2. Producer & Consumer API Requests
- **Producer (Cart Service)**  
  - Endpoint: `POST http://localhost:8000/create-order`  
  - Purpose: Generates a new order with random items and publishes the `order_created` event when the request body includes `orderId` and `numberOfItems`.
- **Consumer (Order Service)**  
  - Endpoint: `GET http://localhost:8100/order-details?orderId=<orderId>`  
  - Purpose: Retrieves the stored order (after the consumer processes the RabbitMQ event) including the calculated shipping cost.

## 3. Exchange Type
- Chosen exchange: **Topic (`orders_exchange`)**.
- Reason: Topic exchange enables pattern-based routing using routing keys, allowing selective message delivery based on routing key patterns. This provides flexibility for routing messages to specific queues based on order status and order ID patterns.

## 4. Binding Key
- Binding key: **`"new.*"`**.
- Reason: The consumer binds with the pattern `"new.*"` to receive all messages with routing keys starting with "new." followed by any order ID. This allows the queue to receive only new order events while supporting future expansion for different order statuses or routing patterns.

## 5. Exchange & Queue Declaration
- **Cart Service (producer)** declares the `orders_exchange` (Topic type, durable).  
- **Order Service (consumer)** declares its dedicated durable queue (`order_service_new_orders`) and binds it to the existing exchange with pattern `"new.*"`.  
- Reason: Separating responsibilities ensures the producer owns the exchange definition, while the consumer manages its own queue. The consumer uses `get_exchange()` to reference the existing exchange without declaring it, maintaining clear ownership boundaries. Messages are published with routing key format `"new.{orderId}"` (e.g., `"new.ORDER123"`), which matches the `"new.*"` binding pattern.