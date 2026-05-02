"""Inventory management tools for Chef agent.
Updated for 江西冰柜点菜: inventory uses quantity_kg.
"""

from __future__ import annotations

from typing import Any

from app.db.memory import db


def check_inventory(ingredient: str) -> str:
    """Check the current stock level of an ingredient."""
    ing = db.check_inventory(ingredient)
    if not ing:
        return f"未找到食材 '{ingredient}'"
    status = "⚠️ 需要补货" if ing.quantity_kg < ing.min_threshold else "✅ 库存充足"
    return f"📦 {ing.name}: {ing.quantity_kg}{ing.unit} ({status})"


def list_all_inventory() -> str:
    """List all ingredients and their stock levels."""
    ingredients = db.list_inventory()
    if not ingredients:
        return "暂无库存记录。"
    lines = ["📦 食材库存:"]
    for ing in ingredients:
        icon = "⚠️" if ing.quantity_kg < ing.min_threshold else "✅"
        lines.append(f"  {icon} {ing.name}: {ing.quantity_kg}{ing.unit} (最低阈值: {ing.min_threshold}{ing.unit})")
    return "\n".join(lines)


def use_ingredient(name: str, quantity_kg: float) -> str:
    """Use/deduct a quantity (in kg) of an ingredient from inventory."""
    if db.use_ingredient(name, quantity_kg):
        ing = db.check_inventory(name)
        status = "⚠️ 需要补货" if ing and ing.quantity_kg < ing.min_threshold else "✅"
        return f"✅ 已使用 {quantity_kg}{ing.unit} '{name}'。剩余: {ing.quantity_kg}{ing.unit} ({status})"
    return f"❌ 食材 '{name}' 库存不足或不存在。"


def restock_ingredient(name: str, quantity_kg: float) -> str:
    """Restock/add quantity (in kg) to an ingredient in inventory."""
    ing = db.restock(name, quantity_kg)
    if ing:
        return f"✅ 已补货 {name}: +{quantity_kg}{ing.unit}，当前库存: {ing.quantity_kg}{ing.unit}"
    return f"❌ 食材 '{name}' 不存在，请先添加。"


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check stock level of an ingredient in the kitchen",
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
            "description": "List all ingredients and their stock levels in the kitchen",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_ingredient",
            "description": "Deduct ingredient from kitchen inventory (when cooking)",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity_kg": {"type": "number", "description": "Quantity in kilograms"},
                },
                "required": ["name", "quantity_kg"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restock_ingredient",
            "description": "Restock an ingredient in the kitchen",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity_kg": {"type": "number", "description": "Quantity in kilograms"},
                },
                "required": ["name", "quantity_kg"],
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
