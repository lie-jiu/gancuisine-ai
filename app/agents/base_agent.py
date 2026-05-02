"""Abstract base Agent with a complete ReAct (Reasoning + Acting) loop.

Each agent has:
1. A system prompt (persona + role)
2. A set of tool definitions (for LLM function calling)
3. A tool map (string name → callable)
4. A run() method that executes the ReAct loop via LangGraph
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class ReActAgent:
    """Base class for all restaurant agents.

    Implements a complete ReAct loop:
      1. LLM thinks and decides to call a tool (or respond directly)
      2. Tool is executed
      3. Result is fed back to LLM
      4. Repeat until LLM produces a final answer
    """

    name: str = "base"
    system_prompt: str = "You are a helpful restaurant assistant."
    tool_list: list[dict] = []
    tool_map: dict[str, Callable] = {}

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def run(self, user_message: str, max_rounds: int = 8) -> str:
        """Execute the ReAct loop. Returns the final response string."""

        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _round in range(max_rounds):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_list if self.tool_list else None,
                    tool_choice="auto" if self.tool_list else None,
                    temperature=0.3,
                )
            except Exception as e:
                logger.error(f"[{self.name}] LLM call failed: {e}")
                return f"系统错误：无法连接到AI服务（{e}）"

            msg = response.choices[0].message

            # If no tool calls, LLM is responding directly — this is the final answer
            if not msg.tool_calls:
                return msg.content or "（没有回复）"

            # ── Process each tool call ──────────────────────
            messages.append(msg.model_dump(exclude={"function_call"}))

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                func = self.tool_map.get(tool_name)
                if not func:
                    result = f"❌ 未知工具: {tool_name}"
                    logger.warning(f"[{self.name}] Unknown tool: {tool_name}")
                else:
                    try:
                        result = func(**args)
                        logger.info(f"[{self.name}] Called {tool_name}({args}) → {result[:80]}...")
                    except Exception as e:
                        result = f"❌ 工具 '{tool_name}' 执行错误: {e}"
                        logger.exception(f"[{self.name}] Tool {tool_name} failed")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        # If we exhausted rounds without a final answer, generate one
        try:
            final = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            return final.choices[0].message.content or "（处理超时，请重试）"
        except Exception as e:
            return f"处理超时：{e}"
