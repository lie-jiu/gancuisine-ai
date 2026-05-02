"""Billing and payment tools."""

from __future__ import annotations

from typing import Any

from app.db.memory import db
from app.models.schemas import BillItem


def get_bill(table_id: int) -> str:
    """Get the current bill for a table."""
    bill = db.get_or_create_bill(table_id)
    if not bill.items:
        return f"桌号{table_id}暂无账单项目。"

    lines = [f"🧾 桌号 {table_id} 账单:"]
    for i, item in enumerate(bill.items, 1):
        lines.append(f"  {i}. {item.description} x{item.quantity} — ¥{item.unit_price:.0f}/份")
    lines.append(f"  ─────────────────")
    lines.append(f"  小计: ¥{bill.subtotal:.2f}")
    lines.append(f"  服务费(10%): ¥{bill.service_charge:.2f}")
    lines.append(f"  税费(6%): ¥{bill.tax:.2f}")
    lines.append(f"  💰 总计: ¥{bill.total:.2f}")
    lines.append(f"  支付状态: {'✅ 已支付' if bill.paid else '⏳ 未支付'}")
    return "\n".join(lines)


def add_to_bill(table_id: int, description: str, quantity: int, unit_price: float) -> str:
    """Add an item to a table's bill."""
    item = BillItem(description=description, quantity=quantity, unit_price=unit_price)
    bill = db.add_to_bill(table_id, [item])
    return f"✅ 已添加 '{description}' 到桌号{table_id}的账单。当前总计: ¥{bill.total:.2f}"


def pay_bill(table_id: int) -> str:
    """Process payment for a table's bill."""
    bill = db.pay_bill(table_id)
    if not bill:
        return f"❌ 桌号{table_id}暂无账单。"
    if bill.paid:
        return f"✅ 桌号{table_id}账单已支付！总计 ¥{bill.total:.2f}。感谢惠顾！"
    return "❌ 支付失败。"


def split_bill(table_id: int, num_people: int) -> str:
    """Split the bill equally among a number of people."""
    bill = db.get_or_create_bill(table_id)
    if not bill.items:
        return f"桌号{table_id}没有可分的账单。"
    per_person = round(bill.total / num_people, 2)
    return (
        f"💳 桌号 {table_id} 账单均分 ({num_people}人):\n"
        f"  总计: ¥{bill.total:.2f}\n"
        f"  每人: ¥{per_person:.2f}"
    )


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_bill",
            "description": "Get the current bill for a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "integer"},
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_bill",
            "description": "Add an item to a table's bill",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "integer"},
                    "description": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "unit_price": {"type": "number"},
                },
                "required": ["table_id", "description", "quantity", "unit_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pay_bill",
            "description": "Process payment for a table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "integer"},
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "split_bill",
            "description": "Split the bill equally among a number of people",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "integer"},
                    "num_people": {"type": "integer"},
                },
                "required": ["table_id", "num_people"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "get_bill": get_bill,
    "add_to_bill": add_to_bill,
    "pay_bill": pay_bill,
    "split_bill": split_bill,
}
