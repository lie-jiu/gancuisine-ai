"""FastAPI entry point — REST API for the restaurant multi-agent service."""

from __future__ import annotations

import logging
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.memory import db
from app.graph.workflow import agent_graph
from app.models.schemas import (
    AgentType,
    ChatRequest,
    ChatResponse,
    ConversationTurn,
    OrderItem,
    OrderStatus,
    ReservationStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("restaurant-api")

app = FastAPI(
    title="Restaurant Multi-Agent Service",
    description="An intelligent restaurant service system powered by LangGraph multi-agent orchestration.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════
# Conversation / Chat
# ═══════════════════════════════════════════════════════

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Start a new conversation."""
    session_id = uuid.uuid4().hex[:12]
    conv = db.get_or_create_conversation(session_id)
    conv.customer_name = request.customer_name

    db.add_turn(conv, "customer", request.message)

    result = agent_graph.invoke({
        "customer_message": request.message,
        "context": "",
        "messages": [],
        "routed_agent": "",
        "agent_response": "",
        "escalation": False,
    })

    response = result.get("agent_response", "欢迎光临！")
    agent_name = result.get("routed_agent", "supervisor")
    db.add_turn(conv, "agent", response, agent_name)

    return ChatResponse(
        session_id=session_id,
        response=response,
        agent=AgentType(agent_name) if agent_name in AgentType._value2member_map_ else AgentType.supervisor,
    )


@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_continue(session_id: str, request: ChatRequest):
    """Continue an existing conversation."""
    conv = db.get_or_create_conversation(session_id)
    db.add_turn(conv, "customer", request.message)

    # Build context from last few turns
    context = "\n".join(
        f"{'顾客' if t.role == 'customer' else t.agent.value}: {t.message}"
        for t in conv.turns[-6:]
    )

    result = agent_graph.invoke({
        "customer_message": request.message,
        "context": context,
        "messages": [],
        "routed_agent": "",
        "agent_response": "",
        "escalation": False,
    })

    response = result.get("agent_response", "欢迎光临！")
    agent_name = result.get("routed_agent", "supervisor")
    db.add_turn(conv, "agent", response, agent_name)

    return ChatResponse(
        session_id=session_id,
        response=response,
        agent=AgentType(agent_name) if agent_name in AgentType._value2member_map_ else AgentType.supervisor,
    )


@app.get("/chat/{session_id}")
async def get_conversation(session_id: str):
    """Get full conversation history."""
    conv = db.get_or_create_conversation(session_id)
    return {
        "session_id": session_id,
        "customer_name": conv.customer_name,
        "turns": [
            {
                "role": t.role,
                "agent": t.agent.value,
                "message": t.message,
                "time": t.timestamp.isoformat(),
            }
            for t in conv.turns
        ],
    }


@app.delete("/chat/{session_id}")
async def clear_conversation(session_id: str):
    """Clear a conversation."""
    if session_id in db.conversations:
        del db.conversations[session_id]
    return {"status": "cleared"}


# ═══════════════════════════════════════════════════════
# Reservations
# ═══════════════════════════════════════════════════════

@app.post("/reservations")
async def create_reservation(
    customer_name: str, party_size: int, time: str,
    phone: str = "", table_id: int | None = None, special_requests: str = "",
):
    """Create a new reservation. `time` should be ISO format."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(time)
    except ValueError:
        raise HTTPException(400, "Invalid time format. Use ISO format e.g. 2025-12-25T18:00")

    tables = db.get_available_tables(party_size)
    if not tables and not table_id:
        raise HTTPException(400, f"No available tables for {party_size} people")

    tid = table_id or tables[0].id
    res = db.create_reservation(customer_name, phone, party_size, dt, tid, special_requests)
    return res.model_dump()


@app.get("/reservations")
async def list_reservations():
    """List all reservations."""
    return [r.model_dump() for r in db.list_reservations()]


@app.get("/reservations/{res_id}")
async def get_reservation(res_id: str):
    """Get a reservation by ID."""
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(404, "Reservation not found")
    return res.model_dump()


@app.delete("/reservations/{res_id}")
async def cancel_reservation(res_id: str):
    """Cancel a reservation."""
    if db.cancel_reservation(res_id):
        return {"status": "cancelled", "id": res_id}
    raise HTTPException(404, "Reservation not found")


# ═══════════════════════════════════════════════════════
# Menu
# ═══════════════════════════════════════════════════════

@app.get("/menu")
async def get_menu(category: str | None = None):
    """Get the menu, optionally filtered by category."""
    from app.tools.menu import get_menu
    return get_menu(category)


# ═══════════════════════════════════════════════════════
# Orders
# ═══════════════════════════════════════════════════════

@app.post("/orders")
async def create_order(table_id: int, customer_name: str = ""):
    """Create a new order for a table."""
    order = db.create_order(table_id, customer_name)
    return order.model_dump()


@app.post("/orders/{order_id}/items")
async def add_order_item(order_id: str, menu_item_id: int, quantity: int = 1, notes: str = ""):
    """Add an item to an order."""
    item = OrderItem(menu_item_id=menu_item_id, quantity=quantity, notes=notes)
    order = db.add_order_item(order_id, item)
    if not order:
        raise HTTPException(404, "Order not found")
    return order.model_dump()


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details."""
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order.model_dump()


@app.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    """Update order status (pending/confirmed/preparing/ready/served/cancelled)."""
    try:
        s = OrderStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status. Must be one of: {[e.value for e in OrderStatus]}")
    order = db.update_order_status(order_id, s)
    if not order:
        raise HTTPException(404, "Order not found")
    return order.model_dump()


# ═══════════════════════════════════════════════════════
# Inventory
# ═══════════════════════════════════════════════════════

@app.get("/inventory")
async def list_inventory():
    """List all ingredients in inventory."""
    from app.tools.inventory import list_all_inventory
    return list_all_inventory()


@app.post("/inventory/restock")
async def restock(name: str, quantity: float):
    """Restock an ingredient."""
    from app.tools.inventory import restock_ingredient
    return restock_ingredient(name, quantity)


# ═══════════════════════════════════════════════════════
# Bills
# ═══════════════════════════════════════════════════════

@app.get("/bills/{table_id}")
async def get_bill(table_id: int):
    """Get the bill for a table."""
    from app.tools.billing import get_bill
    return get_bill(table_id)


@app.post("/bills/{table_id}/split")
async def split_bill(table_id: int, num_people: int):
    """Split the bill equally."""
    from app.tools.billing import split_bill
    return split_bill(table_id, num_people)


@app.post("/bills/{table_id}/pay")
async def pay_bill(table_id: int):
    """Process payment for a table."""
    from app.tools.billing import pay_bill
    return pay_bill(table_id)


# ═══════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "service": "restaurant-multi-agent"}


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════

def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
