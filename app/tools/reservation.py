"""Reservation & table management tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.memory import db


def search_available_tables(capacity: int, time: str | None = None) -> str:
    """Search for available tables that can seat {capacity} people."""
    tables = db.get_available_tables(capacity)
    if not tables:
        return f"抱歉，没有能容纳{capacity}人的空桌了。"
    lines = [f"可用桌位（至少{capacity}人）:"]
    for t in tables:
        lines.append(f"  - 桌号{t.id}（{t.capacity}人, {t.location}）")
    return "\n".join(lines)


def make_reservation(
    customer_name: str, party_size: int, time_str: str,
    phone: str = "", special_requests: str = "",
) -> str:
    """Create a reservation for {customer_name}, {party_size} people at {time_str}.

    time_str should be like '2025-12-25 18:00'.
    Returns confirmation or error.
    """
    try:
        dt = datetime.fromisoformat(time_str)
    except ValueError:
        return f"时间格式错误，请使用 ISO 格式如 2025-12-25T18:00"

    tables = db.get_available_tables(party_size)
    if not tables:
        return f"抱歉，{party_size}人时段内没有可用桌位。"

    table_id = tables[0].id
    res = db.create_reservation(
        customer=customer_name, phone=phone, party_size=party_size,
        time=dt, table_id=table_id, special_requests=special_requests,
    )
    return (
        f"✅ 预订成功！\n"
        f"  预订编号：{res.id}\n"
        f"  顾客：{customer_name}\n"
        f"  人数：{party_size}\n"
        f"  时间：{dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"  桌号：{table_id}（{db.tables[table_id].location}）\n"
        f"  备注：{special_requests or '无'}"
    )


def cancel_reservation(reservation_id: str) -> str:
    """Cancel a reservation by its ID."""
    if db.cancel_reservation(reservation_id):
        return f"✅ 预订 {reservation_id} 已取消。"
    return f"❌ 未找到预订 {reservation_id}。"


def get_reservation_details(reservation_id: str) -> str:
    """Get details of a reservation."""
    res = db.get_reservation(reservation_id)
    if not res:
        return f"未找到预订 {reservation_id}"
    return (
        f"预订 {res.id}: {res.customer_name} {res.party_size}人 "
        f"于 {res.time.strftime('%Y-%m-%d %H:%M')} "
        f"状态: {res.status.value}"
    )


def list_all_reservations() -> str:
    """List all reservations."""
    reservations = db.list_reservations()
    if not reservations:
        return "暂无预订记录。"
    lines = ["📋 所有预订:"]
    for r in reservations:
        lines.append(
            f"  {r.id} | {r.customer_name} | {r.party_size}人 | "
            f"{r.time.strftime('%m-%d %H:%M')} | {r.status.value}"
        )
    return "\n".join(lines)


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "search_available_tables",
            "description": "Search for available tables by capacity",
            "parameters": {
                "type": "object",
                "properties": {
                    "capacity": {"type": "integer", "description": "Number of people"},
                    "time": {"type": "string", "description": "Optional time string"},
                },
                "required": ["capacity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_reservation",
            "description": "Create a new reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "time_str": {"type": "string", "description": "ISO format time"},
                    "phone": {"type": "string"},
                    "special_requests": {"type": "string"},
                },
                "required": ["customer_name", "party_size", "time_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                },
                "required": ["reservation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reservation_details",
            "description": "Get details of a reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {"type": "string"},
                },
                "required": ["reservation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_reservations",
            "description": "List all reservations",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "search_available_tables": search_available_tables,
    "make_reservation": make_reservation,
    "cancel_reservation": cancel_reservation,
    "get_reservation_details": get_reservation_details,
    "list_all_reservations": list_all_reservations,
}
