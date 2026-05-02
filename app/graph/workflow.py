"""LangGraph workflow — orchestrates the multi-agent collaboration as a state graph.

Architecture:
  Customer → Supervisor → [Specialist Agent] → Response

The state graph enables:
- Conditional routing based on intent
- Escalation (e.g., waiter → chef for dietary questions)
- Parallel operations (e.g., check inventory AND start prep)
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.supervisor import SupervisorAgent, AGENT_REGISTRY

logger = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────

class AgentState(TypedDict):
    """The state object flowing through the LangGraph."""
    messages: Annotated[list, add_messages]
    customer_message: str
    context: str                  # conversation context for routing
    routed_agent: str             # which agent handled it
    agent_response: str           # the final response
    escalation: bool              # whether escalation is needed


# ── Nodes ──────────────────────────────────────────────

_supervisor = SupervisorAgent()


def router_node(state: AgentState) -> dict:
    """Route the customer message to the appropriate specialist agent."""
    msg = state.get("customer_message", "")
    ctx = state.get("context", "")

    response, agent_name = _supervisor.run(msg, ctx)

    return {
        "routed_agent": agent_name,
        "agent_response": response,
        "messages": [("assistant", f"[{agent_name}]: {response}")],
    }


def escalation_check(state: AgentState) -> Literal["escalated", "resolved"]:
    """Check if the response satisfies the customer or needs escalation."""
    response = state.get("agent_response", "")
    # If the response contains error markers, escalate
    if "❌" in response and "系统错误" not in response:
        return "escalated"
    return "resolved"


def handle_complaint(state: AgentState) -> dict:
    """Handle escalated issues / complaints with the manager's personal touch."""
    complaint_msg = (
        f"顾客说: {state.get('customer_message', '')}\n"
        f"之前回复: {state.get('agent_response', '')}\n"
        f"请以经理身份礼貌地处理这个投诉或问题，提供补偿方案。"
    )
    response = _supervisor._fallback(complaint_msg)
    return {
        "agent_response": f"[经理处理] {response}",
        "escalation": True,
    }


# ── Build Graph ────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the compiled LangGraph workflow."""

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("complaint_handler", handle_complaint)

    # Edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        escalation_check,
        {
            "resolved": END,
            "escalated": "complaint_handler",
        },
    )
    workflow.add_edge("complaint_handler", END)

    return workflow.compile()


# Singleton
agent_graph = build_graph()
