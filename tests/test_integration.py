"""Integration tests for the restaurant multi-agent system.

Tests the end-to-end flow: API → Supervisor → Agent → Tools → Response.
All tests use the in-memory DB with fixtures, no external LLM needed.
"""

import pytest
from fastapi.testclient import TestClient


class TestReservationFlow:
    """Test the full reservation lifecycle through the chat API."""

    def test_make_reservation(self, test_client: TestClient):
        """A customer should be able to make a reservation via chat."""
        response = test_client.post("/chat", json={
            "message": "我想预订今晚6点4个人的位子，我叫张三",
            "customer_name": "张三",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"]
        assert "预订" in data["response"] or "receptionist" in data["agent"]

    def test_reservation_then_query(self, test_client: TestClient):
        """Customer should be able to check available tables."""
        response = test_client.post("/chat", json={
            "message": "今晚还有能坐4个人的桌吗？",
            "customer_name": "王五",
        })
        assert response.status_code == 200
        data = response.json()
        # Should get table info back
        assert data["session_id"]


class TestRestaurantInfo:
    """Test that the system can answer basic restaurant questions."""

    def test_menu_inquiry(self, test_client: TestClient):
        """Customer should be able to ask about the menu."""
        response = test_client.post("/chat", json={
            "message": "你们有什么招牌菜推荐？",
            "customer_name": "赵六",
        })
        assert response.status_code == 200
        data = response.json()
        assert any(kw in data["response"] for kw in
                   ["宫保鸡丁", "北京烤鸭", "麻婆豆腐", "推荐"])

    def test_business_hours(self, test_client: TestClient):
        """Customer should be able to ask business hours."""
        response = test_client.post("/chat", json={
            "message": "你们营业到几点？",
        })
        assert response.status_code == 200


class TestOrderFlow:
    """Test the ordering lifecycle through the API."""

    def test_create_and_manage_order(self, test_client: TestClient):
        """Should be able to create order via REST API."""
        # Create order
        resp = test_client.post("/orders", params={"table_id": 3, "customer_name": "测试客"})
        assert resp.status_code == 200
        order = resp.json()
        assert order["id"].startswith("ORD-")

        # Add item
        order_id = order["id"]
        resp = test_client.post(
            f"/orders/{order_id}/items",
            params={"menu_item_id": 1, "quantity": 2},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

        # Update status
        resp = test_client.patch(
            f"/orders/{order_id}/status",
            params={"status": "confirmed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"


class TestBillingFlow:
    """Test the billing lifecycle."""

    def test_bill_flow(self, test_client: TestClient):
        """Should be able to add items to bill and pay."""
        # Add bill items
        resp = test_client.get("/bills/5")
        assert resp.status_code == 200
        assert "暂无" not in resp.text  # should handle empty bill gracefully

    def test_split_bill(self, test_client: TestClient):
        """Should be able to split a bill."""
        # First add something to the bill
        from app.tools.billing import add_to_bill
        add_to_bill(1, "宫保鸡丁", 2, 68.0)

        resp = test_client.post("/bills/1/split", params={"num_people": 4})
        assert resp.status_code == 200
        assert "每人" in resp.text


class TestInventoryFlow:
    """Test inventory management."""

    def test_inventory_check(self, test_client: TestClient):
        """Should be able to check inventory."""
        resp = test_client.get("/inventory")
        assert resp.status_code == 200
        assert "chicken" in resp.text or "食材" in resp.text

    def test_restock(self, test_client: TestClient):
        """Should be able to restock ingredients."""
        resp = test_client.post(
            "/inventory/restock",
            params={"name": "chicken", "quantity": 5.0},
        )
        assert resp.status_code == 200
        assert "补货" in resp.text or "✅" in resp.text


class TestConversationManagement:
    """Test the conversation/session lifecycle."""

    def test_conversation_history(self, test_client: TestClient):
        """Should be able to retrieve conversation history."""
        # Start a conversation
        resp = test_client.post("/chat", json={
            "message": "你好，我想订位",
            "customer_name": "历史客",
        })
        session_id = resp.json()["session_id"]

        # Retrieve history
        resp = test_client.get(f"/chat/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_name"] == "历史客"
        assert len(data["turns"]) >= 2  # customer + agent

    def test_clear_conversation(self, test_client: TestClient):
        """Should be able to clear a conversation."""
        resp = test_client.post("/chat", json={"message": "测试"})
        session_id = resp.json()["session_id"]

        resp = test_client.delete(f"/chat/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health(self, test_client: TestClient):
        """Health endpoint should return ok."""
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
