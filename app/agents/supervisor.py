"""经理 Agent — the supervisor/orchestrator that routes to specialist agents.

Routes tasks based on intent to the right specialist agent.
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from app.agents.receptionist import ReceptionistAgent
from app.agents.waiter import WaiterAgent
from app.agents.chef import ChefAgent
from app.agents.sommelier import SommelierAgent
from app.config import settings

logger = logging.getLogger(__name__)


# Agent role descriptions for the router LLM
AGENT_REGISTRY = {
    "receptionist": {
        "agent": ReceptionistAgent(),
        "description": "处理预订、座位安排和客人接待咨询",
        "keywords": [
            "预订", "预约", "座位", "订位", "包间", "大厅", "窗边", "露台",
            "reservation", "book", "table", "cancel",
        ],
    },
    "waiter": {
        "agent": WaiterAgent(),
        "description": "点菜引导、冰柜展示、推荐做法、上菜和账单服务",
        "keywords": [
            "冰柜", "有什么", "菜单", "推荐", "点菜", "点餐", "下单",
            "买单", "结账", "order", "menu", "bill", "check", "serve",
            "recommend", "吃什么", "吃啥", "看看", "有什么菜",
        ],
    },
    "chef": {
        "agent": ChefAgent(),
        "description": "厨房制作、食材识别、冰柜扫描、江西做法推荐和库存管理",
        "keywords": [
            "厨房", "制作", "出餐", "食材", "库存", "采购", "补货",
            "kitchen", "cook", "prepare", "inventory", "ingredient",
            "做法", "怎么吃", "怎么做", "识别", "照片", "拍照", "图片",
            "scan", "vision",
        ],
    },
    "sommelier": {
        "agent": SommelierAgent(),
        "description": "酒水推荐和饮品搭配建议",
        "keywords": [
            "酒", "红酒", "白酒", "四特", "啤酒", "米酒",
            "wine", "drink", "pairing", "推荐酒", "喝什么", "干杯",
            "搭配", "饮品",
        ],
    },
}


class RouterLLM:
    """Lightweight LLM router that decides which agent should handle a query."""

    SYSTEM_PROMPT = """你是一个江西特色餐厅的智能路由调度员。
根据用户的问题和可用的服务Agent，选择最合适的Agent来处理。

可用的Agent:
{agents_desc}

回复格式（仅返回JSON，不要有其他文字）:
{{"agent": "agent_name", "reason": "简短的中文理由"}}

注意：
- 如果客人问"吃什么/有什么菜/看看冰柜" → 选 waiter
- 如果客人发照片/问识别/问做法 → 选 chef
- 如果客人要预订 → 选 receptionist
- 如果涉及多个方面，选最主要的
- 无法确定默认选 "waiter"
"""

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def route(self, message: str, context: str = "") -> str:
        """Determine which agent should handle this message. Returns agent name."""
        # Quick keyword-based routing first
        msg_lower = message.lower()
        for name, info in AGENT_REGISTRY.items():
            for kw in info["keywords"]:
                if kw in msg_lower:
                    logger.info(f"[Router] Keyword match '{kw}' → {name}")
                    return name

        # Fall back to LLM routing
        agents_desc = "\n".join(
            f"- {name}: {info['description']}"
            for name, info in AGENT_REGISTRY.items()
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT.format(agents_desc=agents_desc)},
                    {"role": "user", "content": f"对话上下文: {context}\n用户消息: {message}"},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content or "{}")
            agent = result.get("agent", "waiter")
            logger.info(f"[Router] LLM route → {agent} (reason: {result.get('reason', 'N/A')})")
            return agent
        except Exception as e:
            logger.warning(f"[Router] LLM routing failed: {e}, defaulting to waiter")
            return "waiter"


class SupervisorAgent:
    """The manager/supervisor that orchestrates specialist agents."""

    def __init__(self) -> None:
        self.router = RouterLLM()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def run(self, user_message: str, context: str = "") -> tuple[str, str]:
        """Route message to the right agent and return (response, agent_name)."""
        agent_name = self.router.route(user_message, context)
        agent_info = AGENT_REGISTRY.get(agent_name)

        if not agent_info:
            return self._fallback(user_message), "supervisor"

        try:
            response = agent_info["agent"].run(user_message)
            return response, agent_name
        except Exception as e:
            logger.exception(f"[Supervisor] Agent {agent_name} failed")
            return f"抱歉，{agent_name}服务暂时出现问题，请稍后再试。", "supervisor"

    def _fallback(self, message: str) -> str:
        """Fallback when routing fails."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一家江西特色餐厅的经理，热情豪爽地回答客人的各种问题。"},
                    {"role": "user", "content": message},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content or "欢迎光临！来看冰柜，点什么做什么！"
        except Exception:
            return "欢迎光临！来看冰柜，点什么做什么！"
