"""冰柜工具集 — 取代传统菜单系统。

江西特色：没有菜单，食材全部展示在冰柜里，客人看了再点。
"""

from __future__ import annotations

from typing import Any

from app.db.memory import db
from app.models.schemas import IngredientCategory, CookingMethod


CATEGORY_LABELS = {
    IngredientCategory.meat: "🥩 肉类",
    IngredientCategory.poultry: "🍗 禽类",
    IngredientCategory.seafood: "🦐 水产海鲜",
    IngredientCategory.preserved: "🥓 赣味腊品",
    IngredientCategory.vegetable: "🥬 蔬菜",
    IngredientCategory.tofu_egg: "🧈 豆制品/蛋类",
}


def show_fridge(category: str | None = None) -> str:
    """展示冰柜里有什么食材。

    category 可选: meat, poultry, seafood, preserved, vegetable, tofu_egg
    不传 category 则展示全部冰柜。
    """
    cat_enum = None
    if category:
        try:
            cat_enum = IngredientCategory(category)
        except ValueError:
            return f"分类 '{category}' 不存在。可选: {', '.join(c.value for c in IngredientCategory)}"

    items = db.get_fridge_display(cat_enum)

    if not items:
        return "冰柜里暂时没有食材。"

    if cat_enum:
        label = CATEGORY_LABELS.get(cat_enum, cat_enum.value)
        lines = [f"\n🧊   {label}"]
    else:
        lines = ["🧊 ========== 冰柜展示 =========="]
        lines.append("   江西特色：没有菜单，食材都在冰柜里！\n")
        # 分组展示
        current_cat = None
        for item in items:
            if item.category != current_cat:
                current_cat = item.category
                label = CATEGORY_LABELS.get(current_cat, current_cat.value)
                lines.append(f"\n── {label} ──")
            lines.append(f"  [{item.id:>2}] {item.name_zh:<6} ¥{item.price_per_500g:.0f}/斤  {item.description}")
        lines.append("\n💡 看中什么食材告诉服务员，厨师现场给您做！")
        return "\n".join(lines)

    # 单类别展示
    for item in items:
        lines.append(f"  [{item.id:>2}] {item.name_zh:<6} ¥{item.price_per_500g:.0f}/斤  {item.description}")
    lines.append("\n💡 报食材编号或名字，厨师给您推荐做法！")
    return "\n".join(lines)


def show_fridge_item(item_id: int) -> str:
    """查看冰柜里某样食材的详细信息"""
    item = db.get_fridge_item(item_id)
    if not item:
        return f"冰柜里没有编号 {item_id} 的食材。"
    methods = "、".join(m.value for m in item.suggested_methods)
    return (
        f"🧊 {item.name_zh}（{item.name}）\n"
        f"  分类: {CATEGORY_LABELS.get(item.category, item.category.value)}\n"
        f"  价格: ¥{item.price_per_500g:.0f}/斤\n"
        f"  库存: {item.available_kg}斤\n"
        f"  产地: {item.description}\n"
        f"  季节: {item.season}\n"
        f"  适合做法: {methods}"
    )


def search_fridge(keyword: str) -> str:
    """搜索冰柜里有没有某种食材"""
    items = db.search_fridge(keyword)
    if not items:
        return f"冰柜里没找到「{keyword}」相关的食材。"
    lines = [f"🔍 找到以下食材（搜索: {keyword}）:"]
    for item in items:
        lines.append(f"  [{item.id:>2}] {item.name_zh} ¥{item.price_per_500g:.0f}/斤")
    return "\n".join(lines)


def suggest_dishes(ingredient_ids: list[int]) -> str:
    """根据选中的冰柜食材编号，推荐江西做法。

    示例: suggest_dishes([1, 15]) → 五花肉+辣椒 → 辣椒炒肉 etc.
    """
    suggestions = db.suggest_dishes(ingredient_ids)
    if not suggestions:
        chosen = [db.get_fridge_item(i) for i in ingredient_ids]
        names = "、".join(i.name_zh for i in chosen if i)
        return f"抱歉，{names}目前没有现成的搭配做法，您想怎么吃？厨师可以现做。"

    selected_names = []
    for fid in ingredient_ids:
        item = db.get_fridge_item(fid)
        if item:
            selected_names.append(item.name_zh)

    lines = [f"🧊 你选了: {'、'.join(selected_names)}"]
    lines.append("👨‍🍳 厨师推荐以下做法:\n")
    for s in suggestions:
        lines.append(s.display)
        lines.append("")

    return "\n".join(lines)


# ── Tool definitions for LLM ───────────────────────────

TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "show_fridge",
            "description": "展示冰柜里有什么食材（江西特色：没有菜单，看冰柜点菜）",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [c.value for c in IngredientCategory],
                        "description": "食材分类筛选，不传则展示全部",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_fridge_item",
            "description": "查看冰柜里某样食材的详细信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "食材编号"},
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_fridge",
            "description": "在冰柜中搜索某种食材",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如'肉'、'辣椒'"},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_dishes",
            "description": "根据选中的冰柜食材推荐江西做法",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "冰柜食材编号列表，如 [1, 15] 表示五花肉+辣椒",
                    },
                },
                "required": ["ingredient_ids"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "show_fridge": show_fridge,
    "show_fridge_item": show_fridge_item,
    "search_fridge": search_fridge,
    "suggest_dishes": suggest_dishes,
}
