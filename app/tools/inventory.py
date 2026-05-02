"""Inventory management tools for Chef agent."""

from __future__ import annotations

from typing import Any

from app.db.memory import db


def check_inventory(ingredient: str) -> str:
    """Check the current stock level of an ingredient."""
    ing = db.check_inventory(ingredient)
    if not ing:
        return f"未找到食材 '{ingredient}'"
    status = "⚠️ 需要补货" if ing.quantity < ing.min_threshold else "✅ 库存充足"
    return f"📦 {ing.name}: {ing.quantity}{ing.unit} ({status})"


def list_all_inventory() -> str:
    """List all ingredients and their stock levels."""
    ingredients = db.list_inventory()
    if not ingredients:
        return "暂无库存记录。"
    lines = ["📦 食材库存:"]
    for ing in ingredients:
        icon = "⚠️" if ing.quantity < ing.min_threshold else "✅"
        lines.append(f"  {icon} {ing.name}: {ing.quantity}{ing.unit} (最低阈值: {ing.min_threshold}{ing.unit})")
    return "\n".join(lines)


def use_ingredient(name: str, quantity: float) -> str:
    """Use/deduct a quantity of an ingredient from inventory."""
    if db.use_ingredient(name, quantity):
        ing = db.check_inventory(name)
        status = "⚠️ 需要补货" if ing and ing.quantity < ing.min_threshold else "✅"
        return f"✅ 已使用 {quantity}{ing.unit} '{name}'。剩余: {ing.quantity}{ing.unit} ({status})"
    return f"❌ 食材 '{name}' 库存不足或不存在。"


def restock_ingredient(name: str, quantity: float) -> str:
    """Restock/add quantity to an ingredient in inventory."""
    ing = db.restock(name, quantity)
    if ing:
        return f"✅ 已补货 {name}: +{quantity}{ing.unit}，当前库存: {ing.quantity}{ing.unit}"
    return f"❌ 食材 '{name}' 不存在，请先添加。"


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check stock level of an ingredient",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient": {"type": "string"},
                },
                "required": ["ingredient"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_inventory",
            "description": "List all ingredients and their stock levels",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_ingredient",
            "description": "Deduct ingredient from inventory (used when cooking)",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "number"},
                },
                "required": ["name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restock_ingredient",
            "description": "Restock an ingredient",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "number"},
                },
                "required": ["name", "quantity"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "check_inventory": check_inventory,
    "list_all_inventory": list_all_inventory,
    "use_ingredient": use_ingredient,
    "restock_ingredient": restock_ingredient,
}
