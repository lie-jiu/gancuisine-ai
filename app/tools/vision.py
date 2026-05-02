"""视觉识别工具 — 通过照片识别冰柜里的食材。

使用 GPT-4o Vision 分析冰柜照片，识别出蔬菜、肉类等食材，
然后自动匹配冰柜库存并推荐江西做法。
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from openai import OpenAI

from app.config import settings
from app.db.memory import db
from app.models.schemas import (
    CookingMethod,
    FridgeScanResult,
    IdentifiedIngredient,
    IngredientCategory,
)

logger = logging.getLogger(__name__)


VISION_SYSTEM_PROMPT = """你是一位经验丰富的江西菜厨师和食材鉴定专家。

用户会发来一张冰柜（冷藏展示柜）的照片，里面摆放着各种食材（蔬菜、肉类、水产等）。
请仔细分析照片，识别出所有可见的食材。

对于每种识别出的食材，提供：
1. 中文名称
2. 英文名称
3. 类别（vegetable蔬菜/meat肉类/poultry禽类/seafood水产/preserved腊味/tofu_egg豆制品蛋类）
4. 目测大概重量（公斤）
5. 置信度（0-1之间）

以JSON数组格式回复，不要有其他文字：
[
  {
    "name_zh": "五花肉",
    "name": "Pork Belly",
    "category": "meat",
    "estimated_weight_kg": 0.5,
    "confidence": 0.95
  }
]

注意：
- 如果照片里没有食材或无法识别，返回空数组 []
- 类别必须是以下之一：vegetable, meat, poultry, seafood, preserved, tofu_egg, other
- 尽量准确，不要编造照片中没有的食材
"""


def _encode_image(image_path: str) -> str:
    """Read an image file and return base64-encoded data URL."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data


def scan_fridge_photo(image_path: str) -> str:
    """扫描冰柜照片，识别出里面的食材，并推荐江西做法。

    image_path: 冰柜照片的本地路径或URL。
    """
    client = OpenAI(api_key=settings.openai_api_key)

    # Build image content
    if image_path.startswith(("http://", "https://")):
        image_content = {"type": "image_url", "image_url": {"url": image_path, "detail": "high"}}
    else:
        b64 = _encode_image(image_path)
        image_content = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
        }

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "看看冰柜里都有什么食材？"},
                        image_content,
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content or "[]"
        # Clean markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        identified_list = json.loads(raw)

    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return f"❌ 图片识别失败: {e}"

    if not identified_list:
        return "😅 照片里没有识别出食材，请拍一张冰柜展示柜的照片试试。"

    # ── Build result ──
    result = FridgeScanResult()
    fridge_items = db.get_fridge_display()
    fridge_map = {f.name_zh: f for f in fridge_items}

    ingredient_ids = []
    lines = ["📸 冰柜扫描结果：\n"]

    for item in identified_list:
        name_zh = item.get("name_zh", "?")
        cat_str = item.get("category", "other")
        try:
            cat = IngredientCategory(cat_str)
        except ValueError:
            cat = IngredientCategory.other

        identified = IdentifiedIngredient(
            name=item.get("name", name_zh),
            name_zh=name_zh,
            confidence=item.get("confidence", 0.5),
            category=cat,
            estimated_weight_kg=item.get("estimated_weight_kg", 0.5),
        )

        # Try to match with fridge inventory
        matched = None
        for fid, fridge_ing in fridge_map.items():
            if name_zh in fid or fid in name_zh:
                matched = fridge_ing
                break

        if matched:
            identified.matched_fridge_id = matched.id
            ingredient_ids.append(matched.id)
            confidence_str = f" ({identified.confidence:.0%})" if identified.confidence > 0 else ""
            lines.append(f"  ✅ {name_zh} —— 冰柜有货！¥{matched.price_per_500g}/斤{confidence_str}")
        else:
            lines.append(f"  🔍 {name_zh}（未在冰柜中找到精确匹配）")

        result.identified.append(identified)

    # ── Get dish suggestions ──
    if ingredient_ids:
        suggestions = db.suggest_dishes(ingredient_ids)
        result.suggestions = suggestions

        if suggestions:
            lines.append("\n👨‍🍳 结合冰柜食材，推荐以下赣菜做法：\n")
            for s in suggestions[:5]:  # top 5
                lines.append(s.display)
        else:
            lines.append("\n🤔 这些食材暂时没有经典搭配，厨师可以现场发挥！")

    result.raw_analysis = " | ".join(f"{i.name_zh}({i.confidence:.0%})" for i in result.identified)

    return "\n".join(lines)


TOOL_LIST = [
    {
        "type": "function",
        "function": {
            "name": "scan_fridge_photo",
            "description": "扫描冰柜照片，用AI视觉识别出食材并推荐江西做法",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "冰柜照片路径（本地路径或URL）",
                    },
                },
                "required": ["image_path"],
            },
        },
    },
]

TOOL_MAP: dict[str, Any] = {
    "scan_fridge_photo": scan_fridge_photo,
}
