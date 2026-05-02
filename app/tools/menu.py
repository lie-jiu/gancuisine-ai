"""菜单查询 — 江西特色：菜单已被冰柜取代！

保留此模块仅用于向后兼容，实际功能委托给 fridge.py。
"""

from __future__ import annotations

from typing import Any

from app.tools.fridge import show_fridge, show_fridge_item


def get_menu(category: str | None = None) -> str:
    """已废弃：江西特色没有菜单，请使用冰柜展示。"""
    return (
        "🍜 我们江西菜没有菜单！\n\n"
        "请到冰柜前看看今天有什么新鲜食材：\n"
        "  - 🥩 新鲜肉类\n"
        "  - 🥬 当季蔬菜\n"
        "  - 🦐 鄱阳湖水产\n"
        "  - 🥓 赣南腊味\n\n"
        "看中什么告诉服务员，厨师现场给您做！\n"
        "或者您可以让我看看冰柜：'看看冰柜有什么？'"
    )


def get_menu_item_details(item_id: int) -> str:
    """已废弃：查看冰柜食材详情"""
    return show_fridge_item(item_id)


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "查看餐厅能吃什么（江西特色：展示冰柜食材而不是菜单）",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "保留参数，无用",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu_item_details",
            "description": "查看食材详情",
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
