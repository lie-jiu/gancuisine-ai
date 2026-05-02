# GanCuisineAI (赣厨AI) 🧊🔥

**江西冰柜点菜 · 多Agent智能服务系统**

没有菜单，冰柜里有什么吃什么！A Jiangxi-style "fridge-to-table" multi-agent restaurant service system. Powered by **LangGraph** orchestration with 5 specialist agents — each with a complete ReAct (Reason + Act + Observe) loop — working together to deliver an authentic Jiangxi dining experience: guests pick ingredients from the refrigerated display, and the AI recommends classic Gan (赣) cuisine preparations on the spot.

> 🇨🇳 **江西特色**：真正的江西餐厅没有纸质菜单——所有食材都摆在冰柜里，客人看了实物再点菜。GanCuisineAI 把这种体验搬到了线上。

---

## 🏗️ Architecture

```
                ┌─────────────────┐
                │    Supervisor   │
                │  (ManagerAgent) │
                └────────┬────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Reception  │  │    Waiter   │  │    Chef     │
│  (前台接待)  │  │  (服务员)    │  │   (厨师)     │
│   📋 预订   │  │  🧊 看冰柜   │  │   🔪 现做    │
└─────────────┘  └──────┬──────┘  └─────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │      🧊 冰柜食材         │
          │    (Fridge/数据源)       │
          └────────────┬────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│   Sommelier     │      │  📸 Vision      │
│   (侍酒师)       │      │  GPT-4o 视觉     │
│    🍶 配酒      │      │   识别食材       │
└─────────────────┘      └─────────────────┘
```

### Agent Roles

| Agent | Role | 角色 | Responsibilities |
|-------|------|------|------------------|
| **Supervisor** | 经理 | Manager | Orchestrates workflow, routes intents, handles escalation |
| **Receptionist** | 前台接待 | Reception | Reservations, seating, table management, guest info |
| **Waiter** | 服务员 | Server | **Guides guests to the fridge**, shows ingredients, suggests classic Gan dishes, takes orders |
| **Chef** | 厨师长 | Chef | Identifies ingredients from **fridge photos** (Vision), recommends cooking methods, manages inventory & kitchen |
| **Sommelier** | 侍酒师 | Drinks | Recommends local drinks (四特酒, 南昌啤酒, 庐山云雾茶, 自酿米酒) — pairs with Gan cuisine |

### Core Concept: The Fridge 🧊

Traditional menus are **replaced** by a virtual refrigerated display (冰柜) containing seasonal Jiangxi ingredients:

- 🥩 Meats: 五花肉, 猪排骨, 牛腱子, 本地土鸡, etc.
- 🥬 Vegetables: 藜蒿, 本地辣椒, 蒜苔, 莴笋, 莲藕, 冬笋, etc.
- 🥓 Preserved: 腊肉, 腊肠, 板鸭, 酒糟鱼
- 🧈 Tofu & Eggs: 农家豆腐, 熏干, 土鸡蛋, 腐竹

Guests browse the fridge, pick ingredients, and the AI **suggests authentic Jiangxi recipes** (藜蒿炒腊肉, 辣椒炒肉, 粉蒸肉, 瓦罐汤...) — just like a real 赣菜 restaurant.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- OpenAI API key (for LLM calls + **GPT-4o Vision** for fridge photo scanning)

### Local Development

```bash
# Clone and enter
git clone https://github.com/lie-jiu/gancuisine-ai.git && cd gancuisine-ai

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

API Docs: `http://localhost:8000/docs` (Swagger UI)

---

## 📋 API Endpoints

### 🧊 Fridge (核心功能 — 冰柜)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/fridge` | 🧊 展示冰柜全部食材（支持 `?category=` 筛选） |
| GET | `/fridge/{item_id}` | 查看某样食材详情 + 适合的做法 |
| GET | `/fridge/search/{keyword}` | 🔍 搜索冰柜里的食材 |
| POST | `/fridge/suggest` | 根据选中的食材编号推荐江西做法 |
| POST | `/fridge/scan` | 📸 **上传冰柜照片**，AI自动识别食材并推荐赣菜 |
| POST | `/fridge/scan-url` | 📸 通过图片URL扫描冰柜 |

### 💬 Conversation & Agent Interaction

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | 和AI服务员聊天（看冰柜、点菜、预订、结账） |
| POST | `/chat/{session_id}` | 继续对话 |
| GET | `/chat/{session_id}` | 获取对话历史 |
| DELETE | `/chat/{session_id}` | 清除对话 |

### 📋 Reservation Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reservations` | 创建预订 |
| GET | `/reservations` | 查看所有预订 |
| GET | `/reservations/{id}` | 查看预订详情 |
| DELETE | `/reservations/{id}` | 取消预订 |

### 🍽️ Order Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/orders` | 下订单 |
| GET | `/orders/{id}` | 查看订单状态 |
| PATCH | `/orders/{id}/status` | 更新订单状态 |

### 📦 Inventory & Kitchen

| Method | Path | Description |
|--------|------|-------------|
| GET | `/inventory` | 查看食材库存 |
| POST | `/inventory/restock` | 补货 |

### 💰 Billing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/bills/{table_id}` | 查看账单 |
| POST | `/bills/{table_id}/split` | 分账 |
| POST | `/bills/{table_id}/pay` | 结账 |

---

## 💬 Example Usage

```python
import httpx

BASE = "http://localhost:8000"

# 1️⃣ 看冰柜里有什么
resp = httpx.get(f"{BASE}/fridge")
print(resp.json())

# 2️⃣ 上传冰柜照片识别食材
with open("fridge_photo.jpg", "rb") as f:
    resp = httpx.post(f"{BASE}/fridge/scan", files={"file": f})
print(resp.json())

# 3️⃣ 和AI聊天
resp = httpx.post(f"{BASE}/chat", json={
    "message": "今晚有几位朋友来，我想先看看冰柜里有什么菜"
})
print(resp.json()["response"])
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest -v

# With coverage
pytest --cov=app tests/ -v
```

Current test coverage:
- **Unit tests** (test_agents.py): 11 tests — fridge, kitchen, inventory, billing → ✅ All pass
- **Integration tests** (test_integration.py): 12 tests — fridge display, dish suggestions, order flow, chat, billing, reservation → 10/12 pass (2 chat tests require `OPENAI_API_KEY`)

---

## 📁 Project Structure

```
gancuisine-ai/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point (江西冰柜点菜系统)
│   ├── config.py            # Configuration (OpenAI, server settings)
│   ├── agents/
│   │   ├── base_agent.py    # Abstract base with ReAct loop
│   │   ├── supervisor.py    # ManagerAgent — intent router
│   │   ├── receptionist.py  # 前台接待 Agent (reservations)
│   │   ├── waiter.py        # 服务员 Agent — guides guests to fridge 🧊
│   │   ├── chef.py          # 厨师长 Agent — vision + cooking 🔪
│   │   └── sommelier.py     # 侍酒师 Agent — 四特酒/南昌啤酒 🍶
│   ├── tools/
│   │   ├── fridge.py        # 🧊 冰柜工具集 — browse, search, suggest dishes
│   │   ├── vision.py        # 📸 GPT-4o Vision — scan fridge photos
│   │   ├── reservation.py   # Reservation CRUD tools
│   │   ├── kitchen.py       # Kitchen/order prep tools
│   │   ├── billing.py       # Billing/payment tools
│   │   └── inventory.py     # Ingredient inventory tools
│   ├── graph/
│   │   └── workflow.py      # LangGraph state graph
│   ├── models/
│   │   └── schemas.py       # Pydantic models (FridgeIngredient, etc.)
│   └── db/
│       └── memory.py        # In-memory state store + fridge data
├── tests/
│   ├── test_agents.py       # 11 unit tests
│   └── test_integration.py  # 12 integration tests
├── scripts/
│   └── seed_data.py
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 🧠 How It Works

### The 江西 Dining Experience

```
客人走进餐厅       → 没有菜单，先看冰柜
看冰柜（/fridge）  → 浏览食材：五花肉、藜蒿、腊肉…
选食材              → 报编号或发照片
AI推荐赣菜做法     → 辣椒炒肉、藜蒿炒腊肉、瓦罐汤…
下单到厨房          → 厨师现做
配酒建议            → 四特酒或南昌啤酒
结账买单            → 一站式搞定
```

### Agent Flow

1. **Customer browses fridge** → `GET /fridge` — ingredients displayed by category
2. **Or uploads a fridge photo** → `POST /fridge/scan` — **GPT-4o Vision** identifies ingredients automatically
3. **Customer picks ingredients** → `POST /fridge/suggest` — Chef recommends classic Jiangxi recipes
4. **Customer talks naturally** → `POST /chat` — Supervisor routes to the right specialist agent
5. **Specialist Agent** runs its ReAct loop:
   - **Think**: analyzes the query
   - **Act**: calls tools (fridge, vision, kitchen, billing, etc.)
   - **Observe**: processes tool results
6. **Supervisor** collects results → natural language response

### Technical Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | LangGraph (StateGraph) |
| **Agent Loop** | Custom ReAct (Think → Act → Observe) |
| **API Server** | FastAPI + uvicorn |
| **LLM** | OpenAI (GPT-4o / GPT-4o-mini) |
| **Vision** | GPT-4o Vision (fridge photo → ingredient recognition) |
| **Deployment** | Docker Compose |
| **Testing** | pytest with asyncio support |
| **Data** | In-memory store (fridge inventory, reservations, orders) |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required for agents + vision) |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model for agent reasoning |
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |

---

## 📄 License

MIT

---

<p align="center">
  🧊 <b>没有菜单，冰柜就是菜单</b> 🧊<br>
  <i>GanCuisineAI — 把江西的冰柜文化带到线上</i>
</p>
