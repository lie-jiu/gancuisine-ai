# Restaurant Multi-Agent Service

An intelligent restaurant service system powered by **LangGraph** multi-agent orchestration. Each agent has a complete ReAct (Reasoning + Acting) loop, working together to deliver a full dining experience — from reservation to billing.

## 🏗️ Architecture

```
                    ┌──────────────────┐
                    │    Supervisor    │
                    │   (ManagerAgent) │
                    └──────┬──┬──┬─────┘
                           │  │  │
              ┌────────────┘  │  └────────────┐
              ▼               ▼                ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │Reception  │   │  Waiter  │   │  Chef    │
       │(前台接待)│   │ (服务员) │   │ (厨师)   │
       └──────────┘   └──────────┘   └──────────┘
                                       │
                                       ▼
                               ┌──────────┐
                               │Sommelier │
                               │ (侍酒师) │
                               └──────────┘
```

### Agent Roles

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **Supervisor** | 经理 | Orchestrates workflow, routes tasks to agents, handles complaints |
| **Receptionist** | 前台接待 | Reservations, seating, guest inquiries, table management |
| **Waiter** | 服务员 | Order taking, serving, bill splitting, customer interaction |
| **Chef** | 厨师 | Menu management, order preparation, ingredient inventory, dietary adaptations |
| **Sommelier** | 侍酒师 | Wine pairing recommendations, beverage menu, drink service |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- OpenAI API key (or compatible LLM endpoint)

### Local Development

```bash
# Clone and enter
git clone <your-repo-url> && cd restaurant-multi-agent-service

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, seed demo data
python scripts/seed_data.py
```

### Docker Deployment

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

API Docs: `http://localhost:8000/docs` (Swagger UI)

## 📋 API Endpoints

### Conversation & Agent Interaction

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a customer message, get agent response |
| POST | `/chat/{session_id}` | Continue an existing conversation |
| GET | `/chat/{session_id}` | Get conversation history |
| DELETE | `/chat/{session_id}` | Clear a conversation |

### Reservation Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reservations` | Create a new reservation |
| GET | `/reservations` | List all reservations |
| GET | `/reservations/{id}` | Get reservation details |
| DELETE | `/reservations/{id}` | Cancel a reservation |

### Menu & Order Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/menu` | Get full menu |
| POST | `/orders` | Place a new order |
| GET | `/orders/{id}` | Get order status |
| PATCH | `/orders/{id}/status` | Update order status |

### Inventory & Kitchen

| Method | Path | Description |
|--------|------|-------------|
| GET | `/inventory` | Check ingredient inventory |
| POST | `/inventory/restock` | Restock ingredients |

### Billing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/bills/{table_id}` | Get bill for a table |
| POST | `/bills/{table_id}/split` | Split bill between guests |
| POST | `/bills/{table_id}/pay` | Process payment |

## 💬 Example Usage

```python
import httpx

# Start a conversation
resp = httpx.post("http://localhost:8000/chat", json={
    "message": "我想预订今晚6点4个人的位子",
    "customer_name": "张三"
})
print(resp.json()["response"])

# Continue the conversation
session_id = resp.json()["session_id"]
resp = httpx.post(f"http://localhost:8000/chat/{session_id}", json={
    "message": "有没有靠窗的座位？"
})
print(resp.json()["response"])
```

## 🧪 Running Tests

```bash
# Run all tests
pytest -v

# With coverage
pytest --cov=app tests/ -v
```

## 📁 Project Structure

```
restaurant-multi-agent-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration (OpenAI, server settings)
│   ├── agents/
│   │   ├── base_agent.py    # Abstract base with ReAct loop
│   │   ├── supervisor.py    # ManagerAgent — workflow orchestrator
│   │   ├── receptionist.py  # 前台接待 Agent
│   │   ├── waiter.py        # 服务员 Agent
│   │   ├── chef.py          # 厨师 Agent
│   │   └── sommelier.py     # 侍酒师 Agent
│   ├── tools/
│   │   ├── reservation.py   # Reservation CRUD tools
│   │   ├── menu.py          # Menu query tools
│   │   ├── kitchen.py       # Kitchen/order prep tools
│   │   ├── billing.py       # Billing/payment tools
│   │   └── inventory.py     # Ingredient inventory tools
│   ├── graph/
│   │   └── workflow.py      # LangGraph state graph
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── db/
│       └── memory.py        # In-memory state store
├── tests/
│   ├── test_receptionist.py
│   ├── test_chef.py
│   ├── test_waiter.py
│   ├── test_sommelier.py
│   └── test_integration.py
├── scripts/
│   └── seed_data.py
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

## 🧠 How It Works

1. **Customer sends a message** → POST `/chat` with natural language
2. **Supervisor Agent** analyzes the intent and routes to the appropriate specialist agent
3. **Specialist Agent** (e.g., Receptionist, Waiter, Chef) runs its ReAct loop:
   - **Think**: analyzes the query and decides what to do
   - **Act**: calls tools (reserve table, check menu, prepare dish, etc.)
   - **Observe**: processes tool results
   - Repeat until the task is complete
4. **Supervisor** collects the result and crafts a natural language response
5. **Response returned** to the customer

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model for agents |
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server port |

## 📄 License

MIT
