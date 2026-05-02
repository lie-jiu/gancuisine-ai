"""经理 Agent — the supervisor/orchestrator that routes to specialist agents."""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from app.agents.base_agent import ReActAgent
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
        "keywords": ["预订", "预约", "座位", "订位", "包间", "大厅", "窗边", "露台",
                     "reservation", "book", "table", "cancel"],
    },
    "waiter": {
        "agent": WaiterAgent(),
        "description": "点餐、上菜、账单和分账服务",
        "keywords": ["点菜", "点餐", "菜单", "推荐", "下单", "买单", "结账",
                     "order", "menu", "bill", "check", "serve", "recommend",
                     "宫保鸡丁", "麻婆豆腐", "北京烤鸭", "炒饭", "春卷", "甜品",
                     "菜单", "有什么菜", "来一份", "招牌"],
    },
    "chef": {
        "agent": ChefAgent(),
        "description": "厨房制作、食材库存和出餐管理",
        "keywords": ["厨房", "制作", "出餐", "食材", "库存", "采购", "补货",
                     "kitchen", "cook", "prepare", "inventory", "ingredient"],
    },
    "sommelier": {
        "agent": SommelierAgent(),
        "description": "酒水推荐和饮品搭配建议",
        "keywords": ["酒", "红酒", "白酒", "茅台", "葡萄酒", "搭配", "饮品",
                     "wine", "drink", "pairing", "推荐酒", "喝什么", "干杯"],
    },
}


class RouterLLM:
    """Lightweight LLM router that decides which agent should handle a query."""

    SYSTEM_PROMPT = """你是一个餐厅服务系统的智能路由调度员。
根据用户的问题和可用的服务Agent，选择最合适的Agent来处理。

可用的Agent:
{agents_desc}

回复格式（仅返回JSON，不要有其他文字）:
{{"agent": "agent_name", "reason": "简短的中文理由"}}

如果用户的问题涉及多个方面，选择最主要的那个Agent。
如果无法确定，默认选择 "receptionist"。
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
            agent = result.get("agent", "receptionist")
            logger.info(f"[Router] LLM route → {agent} (reason: {result.get('reason', 'N/A')})")
            return agent
        except Exception as e:
            logger.warning(f"[Router] LLM routing failed: {e}, defaulting to receptionist")
            return "receptionist"


class SupervisorAgent:
    """The manager/supervisor that orchestrates specialist agents.

    This agent doesn't run a ReAct loop itself — instead it:
    1. Analyzes the customer message
    2. Routes to the right specialist agent
    3. Returns the specialist's response
    """

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
                    {"role": "system", "content": "你是一家高端中餐厅的经理，温和有礼地回答客人的各种问题。"},
                    {"role": "user", "content": message},
                ],
                temperature=0.3,
            )
            return resp.choices[0].message.content or "欢迎光临！"
        except Exception:
            return "欢迎光临我们的餐厅！请问有什么可以帮您的？"
