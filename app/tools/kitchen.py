"""Kitchen / order preparation tools for Chef agent."""

from __future__ import annotations

from typing import Any

from app.db.memory import db
from app.models.schemas import OrderItem, OrderStatus


def create_order(table_id: int, customer_name: str = "") -> str:
    """Create a new order for a table."""
    order = db.create_order(table_id, customer_name)
    return f"✅ 订单已创建: {order.id}（桌号{table_id}）"


def add_item_to_order(order_id: str, menu_item_id: int, quantity: int = 1, notes: str = "") -> str:
    """Add a menu item to an existing order."""
    item = OrderItem(menu_item_id=menu_item_id, quantity=quantity, notes=notes)
    order = db.add_order_item(order_id, item)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    return f"✅ 已添加至订单 {order_id}"


def confirm_order(order_id: str) -> str:
    """Confirm and send an order to the kitchen."""
    order = db.update_order_status(order_id, OrderStatus.confirmed)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    return f"✅ 订单 {order_id} 已确认，已送达厨房。"


def start_preparing(order_id: str) -> str:
    """Mark an order as being prepared by the kitchen."""
    order = db.update_order_status(order_id, OrderStatus.preparing)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    return f"👨‍🍳 订单 {order_id} 开始制作..."


def mark_order_ready(order_id: str) -> str:
    """Mark an order as ready to serve."""
    order = db.update_order_status(order_id, OrderStatus.ready)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    return f"✅ 订单 {order_id} 已完成，准备上菜！"


def mark_order_served(order_id: str) -> str:
    """Mark an order as served to the customer."""
    order = db.update_order_status(order_id, OrderStatus.served)
    if not order:
        return f"❌ 未找到订单 {order_id}"
    return f"✅ 订单 {order_id} 已上菜。"


def get_order_status(order_id: str) -> str:
    """Get the current status of an order."""
    order = db.get_order(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    items_str = "; ".join(f"{i.menu_item_name}x{i.quantity}" for i in order.items)
    return (
        f"📋 订单 {order.id}\n"
        f"  桌号: {order.table_id}\n"
        f"  状态: {order.status.value}\n"
        f"  菜品: {items_str or '无'}\n"
        f"  总额: ¥{order.total:.2f}"
    )


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create a new empty order for a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "integer"},
                    "customer_name": {"type": "string"},
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_item_to_order",
            "description": "Add a menu item (by ID) to an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "menu_item_id": {"type": "integer"},
                    "quantity": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["order_id", "menu_item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_order",
            "description": "Confirm order and send to kitchen",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_preparing",
            "description": "Kitchen starts preparing an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_order_ready",
            "description": "Mark order as ready to serve",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_order_served",
            "description": "Mark order as served to customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Check the status of an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                },
                "required": ["order_id"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "create_order": create_order,
    "add_item_to_order": add_item_to_order,
    "confirm_order": confirm_order,
    "start_preparing": start_preparing,
    "mark_order_ready": mark_order_ready,
    "mark_order_served": mark_order_served,
    "get_order_status": get_order_status,
}
