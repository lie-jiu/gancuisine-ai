"""FastAPI entry point — REST API for the restaurant multi-agent service.

江西特色冰柜点菜系统 API。
"""

from __future__ import annotations

import json
import logging
import uuid

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.memory import db
from app.graph.workflow import agent_graph
from app.models.schemas import (
    AgentType,
    ChatRequest,
    ChatResponse,
    CookingMethod,
    OrderStatus,
)
from app.tools.fridge import show_fridge, show_fridge_item, search_fridge, suggest_dishes
from app.tools.vision import scan_fridge_photo

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("restaurant-api")

app = FastAPI(
    title="江西冰柜点菜 · 多Agent服务系统",
    description="江西特色餐厅：没有菜单，冰柜里有什么吃什么！\n多Agent智能协作系统，支持视觉识别食材并推荐赣菜做法。",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════
# 冰柜 (Fridge) — 核心功能
# ═══════════════════════════════════════════════════════

@app.get("/fridge")
async def get_fridge(category: str | None = None):
    """展示冰柜里有什么食材（江西特色：没有菜单，看冰柜点菜）"""
    return show_fridge(category)


@app.get("/fridge/{item_id}")
async def get_fridge_item(item_id: int):
    """查看冰柜里某样食材的详细信息和适合的做法"""
    return show_fridge_item(item_id)


@app.get("/fridge/search/{keyword}")
async def search_fridge_items(keyword: str):
    """搜索冰柜里的食材"""
    return search_fridge(keyword)


@app.post("/fridge/suggest")
async def suggest_dishes_api(ingredient_ids: list[int]):
    """根据选择的冰柜食材编号推荐江西做法"""
    return suggest_dishes(ingredient_ids)


@app.post("/fridge/scan")
async def scan_fridge(file: UploadFile = File(...)):
    """📸 上传冰柜照片，AI自动识别食材并推荐做法！

    上传一张冰柜展示柜的照片，系统会：
    1. 识别出里面的所有食材
    2. 匹配冰柜库存
    3. 推荐赣菜做法
    """
    contents = await file.read()
    temp_path = f"/tmp/fridge_scan_{uuid.uuid4().hex}.jpg"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        result = scan_fridge_photo(temp_path)
        return result
    except Exception as e:
        raise HTTPException(500, f"识别失败: {e}")


@app.post("/fridge/scan-url")
async def scan_fridge_url(image_url: str):
    """📸 通过URL扫描冰柜照片"""
    return scan_fridge_photo(image_url)


# ═══════════════════════════════════════════════════════
# Conversation / Chat
# ═══════════════════════════════════════════════════════

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """和餐厅AI聊天，支持：看冰柜、点菜、推荐做法、预订、结账"""
    session_id = uuid.uuid4().hex[:12]
    conv = db.get_or_create_conversation(session_id)
    conv.customer_name = request.customer_name

    db.add_turn(conv, "customer", request.message)

    result = agent_graph.invoke({
        "customer_message": request.message,
        "context": "",
        "messages": [],
        "routed_agent": "",
        "agent_response": "",
        "escalation": False,
    })

    response = result.get("agent_response", "欢迎光临！来看冰柜，点什么做什么！")
    agent_name = result.get("routed_agent", "waiter")
    db.add_turn(conv, "agent", response, agent_name)

    return ChatResponse(
        session_id=session_id,
        response=response,
        agent=AgentType(agent_name) if agent_name in [e.value for e in AgentType] else AgentType.waiter,
    )


@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_continue(session_id: str, request: ChatRequest):
    """继续对话"""
    conv = db.get_or_create_conversation(session_id)
    db.add_turn(conv, "customer", request.message)

    context = "\n".join(
        f"{'顾客' if t.role == 'customer' else t.agent.value}: {t.message}"
        for t in conv.turns[-6:]
    )

    result = agent_graph.invoke({
        "customer_message": request.message,
        "context": context,
        "messages": [],
        "routed_agent": "",
        "agent_response": "",
        "escalation": False,
    })

    response = result.get("agent_response", "欢迎光临！")
    agent_name = result.get("routed_agent", "waiter")
    db.add_turn(conv, "agent", response, agent_name)

    return ChatResponse(
        session_id=session_id,
        response=response,
        agent=AgentType(agent_name) if agent_name in [e.value for e in AgentType] else AgentType.waiter,
    )


@app.get("/chat/{session_id}")
async def get_conversation(session_id: str):
    """获取对话历史"""
    conv = db.get_or_create_conversation(session_id)
    return {
        "session_id": session_id,
        "customer_name": conv.customer_name,
        "turns": [
            {
                "role": t.role,
                "agent": t.agent.value,
                "message": t.message,
                "time": t.timestamp.isoformat(),
            }
            for t in conv.turns
        ],
    }


@app.delete("/chat/{session_id}")
async def clear_conversation(session_id: str):
    """清除对话"""
    if session_id in db.conversations:
        del db.conversations[session_id]
    return {"status": "cleared"}


# ═══════════════════════════════════════════════════════
# Orders
# ═══════════════════════════════════════════════════════

@app.post("/orders")
async def create_order(table_id: int, customer_name: str = ""):
    """创建新订单"""
    order = db.create_order(table_id, customer_name)
    return order.model_dump()


@app.post("/orders/{order_id}/items")
async def add_order_item(order_id: str, dish_name: str, unit_price: float,
                         cooking_method: str = "小炒", quantity: int = 1,
                         ingredients_used: str = "", notes: str = ""):
    """添加菜品到订单"""
    from app.models.schemas import OrderItem
    item = OrderItem(
        dish_name=dish_name,
        ingredients_used=[s.strip() for s in ingredients_used.split(",") if s.strip()],
        cooking_method=cooking_method,
        quantity=quantity,
        unit_price=unit_price,
        notes=notes,
    )
    order = db.add_order_item(order_id, item)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order.model_dump()


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """获取订单详情"""
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order.model_dump()


@app.patch("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str):
    """更新订单状态"""
    try:
        s = OrderStatus(status)
    except ValueError:
        raise HTTPException(400, f"无效状态. 可选: {[e.value for e in OrderStatus]}")
    order = db.update_order_status(order_id, s)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order.model_dump()


# ═══════════════════════════════════════════════════════
# Reservations
# ═══════════════════════════════════════════════════════

@app.post("/reservations")
async def create_reservation(
    customer_name: str, party_size: int, time: str,
    phone: str = "", table_id: int | None = None, special_requests: str = "",
):
    """创建预订"""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(time)
    except ValueError:
        raise HTTPException(400, "时间格式错误，请使用ISO格式如 2025-12-25T18:00")

    tables = db.get_available_tables(party_size)
    if not tables and not table_id:
        raise HTTPException(400, f"没有可容纳{party_size}人的桌位")

    tid = table_id or tables[0].id
    res = db.create_reservation(customer_name, phone, party_size, dt, tid, special_requests)
    return res.model_dump()


@app.get("/reservations")
async def list_reservations():
    """列出所有预订"""
    return [r.model_dump() for r in db.list_reservations()]


@app.get("/reservations/{res_id}")
async def get_reservation(res_id: str):
    """获取预订详情"""
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(404, "预订不存在")
    return res.model_dump()


@app.delete("/reservations/{res_id}")
async def cancel_reservation(res_id: str):
    """取消预订"""
    if db.cancel_reservation(res_id):
        return {"status": "cancelled", "id": res_id}
    raise HTTPException(404, "预订不存在")


# ═══════════════════════════════════════════════════════
# Inventory
# ═══════════════════════════════════════════════════════

@app.get("/inventory")
async def list_inventory():
    """查看厨房备货库存"""
    from app.tools.inventory import list_all_inventory
    return list_all_inventory()


@app.post("/inventory/restock")
async def restock(name: str, quantity: float):
    """补货"""
    from app.tools.inventory import restock_ingredient
    return restock_ingredient(name, quantity)


# ═══════════════════════════════════════════════════════
# Bills
# ═══════════════════════════════════════════════════════

@app.get("/bills/{table_id}")
async def get_bill(table_id: int):
    """查看账单"""
    from app.tools.billing import get_bill
    return get_bill(table_id)


@app.post("/bills/{table_id}/split")
async def split_bill(table_id: int, num_people: int):
    """均分账单"""
    from app.tools.billing import split_bill
    return split_bill(table_id, num_people)


@app.post("/bills/{table_id}/pay")
async def pay_bill(table_id: int):
    """结账支付"""
    from app.tools.billing import pay_bill
    return pay_bill(table_id)


# ═══════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok", "service": "jiangxi-fridge-restaurant"}


# ═══════════════════════════════════════════════════════

def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
