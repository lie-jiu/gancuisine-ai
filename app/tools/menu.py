"""Menu query tools for waiter & sommelier."""

from __future__ import annotations

from typing import Any

from app.db.memory import db


def get_menu(category: str | None = None) -> str:
    """Get the full menu, optionally filtered by category.

    Categories: appetizer, main, dessert, drink, wine
    """
    items = db.get_menu(category)
    if not items:
        return f"菜单分类 '{category}' 暂无菜品。"

    category_labels = {
        "appetizer": "🥟 前菜",
        "main": "🍛 主菜",
        "dessert": "🍰 甜品",
        "drink": "🍵 饮品",
        "wine": "🍷 酒水",
    }

    lines = []
    if category:
        label = category_labels.get(category, category)
        lines.append(f"📋 {label}:")
    else:
        lines.append("📋 完整菜单:")
        # group by category
        from itertools import groupby
        items_sorted = sorted(items, key=lambda x: x.category)
        for cat, group in groupby(items_sorted, key=lambda x: x.category):
            label = category_labels.get(cat, cat)
            lines.append(f"\n--- {label} ---")
            for item in group:
                lines.append(f"  {item.id:>2}. {item.name_zh} ({item.name}) — ¥{item.price:.0f}")
        return "\n".join(lines)

    for item in items:
        lines.append(f"  {item.id:>2}. {item.name_zh} ({item.name}) — ¥{item.price:.0f}")
    return "\n".join(lines)


def get_menu_item_details(item_id: int) -> str:
    """Get detailed info about a specific menu item by its ID."""
    item = db.get_menu_item(item_id)
    if not item:
        return f"未找到菜品 ID {item_id}"
    return (
        f"🍽️ {item.name_zh} ({item.name})\n"
        f"  分类: {item.category}\n"
        f"  价格: ¥{item.price:.0f}\n"
        f"  描述: {item.description or '暂无'}\n"
        f"  食材: {', '.join(item.ingredients)}\n"
        f"  准备时间: {item.prep_time_minutes}分钟\n"
        f"  可点: {'是' if item.available else '否'}"
    )


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Get the full menu, optionally filtered by category (appetizer/main/dessert/drink/wine)",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["appetizer", "main", "dessert", "drink", "wine"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu_item_details",
            "description": "Get detailed info about a menu item by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                },
                "required": ["item_id"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "get_menu": get_menu,
    "get_menu_item_details": get_menu_item_details,
}
