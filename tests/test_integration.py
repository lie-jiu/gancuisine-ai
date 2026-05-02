"""Integration tests for the 江西冰柜点菜 multi-agent system.

Tests the full flow: 冰柜展示 → 选食材 → 推荐做法 → 下单 → 结账
"""

import os

import pytest
from fastapi.testclient import TestClient


class TestFridgeDisplay:
    """冰柜展示——核心功能测试"""

    def test_show_full_fridge(self, test_client: TestClient):
        """展示全部冰柜食材"""
        resp = test_client.get("/fridge")
        assert resp.status_code == 200
        data = resp.text
        assert "五花肉" in data
        assert "藜蒿" in data
        assert "冰柜" in data or "🧊" in data

    def test_show_fridge_by_category(self, test_client: TestClient):
        """按类别展示冰柜"""
        resp = test_client.get("/fridge?category=meat")
        assert resp.status_code == 200
        assert "五花肉" in resp.text

        resp = test_client.get("/fridge?category=vegetable")
        assert resp.status_code == 200
        assert "藜蒿" in resp.text or "辣椒" in resp.text

    def test_fridge_item_detail(self, test_client: TestClient):
        """查看食材详情"""
        resp = test_client.get("/fridge/1")
        assert resp.status_code == 200
        assert "价" in resp.text or "做法" in resp.text

    def test_search_fridge(self, test_client: TestClient):
        """搜索冰柜"""
        resp = test_client.get("/fridge/search/肉")
        assert resp.status_code == 200
        assert "五花肉" in resp.text

        resp = test_client.get("/fridge/search/辣椒")
        assert resp.status_code == 200
        assert "辣椒" in resp.text


class TestDishSuggestions:
    """菜品推荐测试"""

    def test_suggest_classic_pairing(self, test_client: TestClient):
        """经典搭配：藜蒿+腊肉"""
        resp = test_client.post("/fridge/suggest", json=[11, 14])
        assert resp.status_code == 200
        assert "藜蒿炒腊肉" in resp.text or "推荐" in resp.text

    def test_suggest_chili_meat(self, test_client: TestClient):
        """辣椒+五花肉→辣椒炒肉"""
        resp = test_client.post("/fridge/suggest", json=[1, 15])
        assert resp.status_code == 200
        assert "辣椒炒肉" in resp.text or "推荐" in resp.text

    def test_suggest_soup(self, test_client: TestClient):
        """排骨+莲藕→瓦罐汤"""
        resp = test_client.post("/fridge/suggest", json=[2, 18, 21])
        assert resp.status_code == 200
        assert "瓦罐" in resp.text or "汤" in resp.text


class TestOrderFlow:
    """点单流程测试"""

    def test_create_and_manage_order(self, test_client: TestClient):
        """创建订单并添加菜品"""
        resp = test_client.post("/orders", params={"table_id": 3, "customer_name": "老表"})
        assert resp.status_code == 200
        order = resp.json()
        assert order["id"].startswith("ORD-")

        # Add a dish
        order_id = order["id"]
        resp = test_client.post(
            f"/orders/{order_id}/items",
            params={
                "dish_name": "辣椒炒肉",
                "unit_price": 35,
                "cooking_method": "小炒",
                "quantity": 1,
                "ingredients_used": "五花肉,辣椒",
            },
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


class TestChatFlow:
    """聊天对话测试（需 OPENAI_API_KEY）"""

    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY")
    def test_chat_fridge_inquiry(self, test_client: TestClient):
        """问冰柜有什么"""
        resp = test_client.post("/chat", json={
            "message": "有什么吃的？",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"]
        # Should mention fridge or ingredients
        assert any(kw in data["response"] for kw in ["冰柜", "食材", "来看看"])

    @pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY")
    def test_chat_recommendation(self, test_client: TestClient):
        """问推荐菜"""
        resp = test_client.post("/chat", json={
            "message": "你们有什么招牌菜推荐？",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert any(kw in data["response"] for kw in
                   ["藜蒿炒腊肉", "粉蒸肉", "辣椒炒肉", "推荐"])


class TestBillingFlow:
    """账单测试"""

    def test_bill_lifecycle(self, test_client: TestClient):
        """完整账单流程"""
        # Empty bill
        resp = test_client.get("/bills/5")
        assert resp.status_code == 200

        # Add items (via internal tool)
        from app.tools.billing import add_to_bill
        add_to_bill(5, "辣椒炒肉", 1, 35.0)
        add_to_bill(5, "米饭", 2, 3.0)

        resp = test_client.get("/bills/5")
        assert "辣椒炒肉" in resp.text

        # Split
        resp = test_client.post("/bills/5/split", params={"num_people": 2})
        assert resp.status_code == 200
        assert "每人" in resp.text

        # Pay
        resp = test_client.post("/bills/5/pay")
        assert resp.status_code == 200
        assert "已支付" in resp.text or "✅" in resp.text


class TestReservationFlow:
    """预订测试"""

    def test_make_reservation(self, test_client: TestClient):
        """通过API创建预订"""
        from datetime import datetime, timedelta
        dt = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT19:00")

        resp = test_client.post(
            "/reservations",
            params={
                "customer_name": "老张",
                "party_size": 4,
                "time": dt,
                "phone": "13800138000",
                "special_requests": "要个包间",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"].startswith("RES-")
        assert data["customer_name"] == "老张"
