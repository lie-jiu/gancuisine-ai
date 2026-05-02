"""Pydantic data models / schemas for all entities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────

class TableStatus(str, Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    cancelled = "cancelled"


class ReservationStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class AgentType(str, Enum):
    supervisor = "supervisor"
    receptionist = "receptionist"
    waiter = "waiter"
    chef = "chef"
    sommelier = "sommelier"


# ── Tables ─────────────────────────────────────────────

class Table(BaseModel):
    id: int
    capacity: int
    status: TableStatus = TableStatus.available
    location: str = ""  # e.g. "窗边", "包间", "大厅"


# ── Menu ───────────────────────────────────────────────

class MenuItem(BaseModel):
    id: int
    name: str
    name_zh: str
    category: str          # appetizer, main, dessert, drink, wine
    price: float
    description: str = ""
    ingredients: list[str] = Field(default_factory=list)
    available: bool = True
    prep_time_minutes: int = 15


# ── Orders ─────────────────────────────────────────────

class OrderItem(BaseModel):
    menu_item_id: int
    menu_item_name: str = ""
    quantity: int = 1
    notes: str = ""


class Order(BaseModel):
    id: str
    table_id: int
    customer_name: str = ""
    items: list[OrderItem] = Field(default_factory=list)
    status: OrderStatus = OrderStatus.pending
    created_at: datetime = Field(default_factory=datetime.now)
    total: float = 0.0


# ── Reservations ───────────────────────────────────────

class Reservation(BaseModel):
    id: str
    customer_name: str
    phone: str = ""
    party_size: int
    time: datetime
    table_id: Optional[int] = None
    status: ReservationStatus = ReservationStatus.confirmed
    special_requests: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# ── Inventory ──────────────────────────────────────────

class Ingredient(BaseModel):
    name: str
    quantity: float       # in kg / litres
    unit: str = "kg"
    min_threshold: float = 1.0


# ── Bills ──────────────────────────────────────────────

class BillItem(BaseModel):
    description: str
    quantity: int
    unit_price: float


class Bill(BaseModel):
    table_id: int
    items: list[BillItem] = Field(default_factory=list)
    subtotal: float = 0.0
    service_charge: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    paid: bool = False


# ── Chat / Conversation ────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    customer_name: str = ""


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent: AgentType = AgentType.supervisor


class ConversationTurn(BaseModel):
    role: str  # "customer" | "agent"
    message: str
    agent: AgentType = AgentType.supervisor
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    session_id: str
    customer_name: str = ""
    turns: list[ConversationTurn] = Field(default_factory=list)
    active_order_id: Optional[str] = None
    active_reservation_id: Optional[str] = None
