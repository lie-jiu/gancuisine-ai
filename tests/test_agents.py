"""Tests for individual agent tools and ReAct logic (unit tests)."""

from app.db.memory import db
from app.models.schemas import OrderItem
from app.tools import menu as tools_menu
from app.tools import kitchen as tools_kitchen
from app.tools import billing as tools_billing
from app.tools import inventory as tools_inv
from app.tools import reservation as tools_res


class TestReceptionistTools:
    """Test the reservation tools used by ReceptionistAgent."""

    def test_search_available_tables(self):
        result = tools_res.search_available_tables(4)
        assert "可用桌位" in result
        assert "桌号" in result

    def test_search_available_too_large(self):
        result = tools_res.search_available_tables(20)
        assert "抱歉" in result

    def test_make_and_cancel_reservation(self):
        from datetime import datetime, timedelta
        dt = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT19:00")
        result = tools_res.make_reservation("测试", 2, dt, "13800138000", "无")
        assert "预订成功" in result

        # Get reservation ID from result
        # The ID is in the format "预订编号：RES-XXXXXXXX"
        import re
        match = re.search(r"RES-\w+", result)
        assert match
        res_id = match.group()

        cancel = tools_res.cancel_reservation(res_id)
        assert "已取消" in cancel

    def test_list_reservations(self):
        result = tools_res.list_all_reservations()
        assert "暂无" in result or "预订" in result


class TestMenuTools:
    """Test menu query tools."""

    def test_get_full_menu(self):
        result = tools_menu.get_menu()
        assert "宫保鸡丁" in result
        assert "北京烤鸭" in result

    def test_get_menu_by_category(self):
        result = tools_menu.get_menu("wine")
        assert "红酒" in result
        assert "茅台" in result

    def test_get_menu_item(self):
        result = tools_menu.get_menu_item_details(1)
        assert "宫保鸡丁" in result
        assert "¥68" in result


class TestKitchenTools:
    """Test order/kitchen tools."""

    def test_create_and_process_order(self):
        # Create
        result = tools_kitchen.create_order(5)
        assert "订单已创建" in result
        import re
        order_id = re.search(r"ORD-\w+", result).group()

        # Add item
        result = tools_kitchen.add_item_to_order(order_id, 1, 2, "微辣")
        assert "已添加" in result

        # Confirm
        result = tools_kitchen.confirm_order(order_id)
        assert "已确认" in result

        # Start prep
        result = tools_kitchen.start_preparing(order_id)
        assert "开始制作" in result

        # Ready
        result = tools_kitchen.mark_order_ready(order_id)
        assert "已完成" in result

    def test_order_status(self):
        order = db.create_order(3)
        result = tools_kitchen.get_order_status(order.id)
        assert order.id in result


class TestInventoryTools:
    """Test inventory tools."""

    def test_list_inventory(self):
        result = tools_inv.list_all_inventory()
        assert "chicken" in result

    def test_use_and_check(self):
        result = tools_inv.check_inventory("chicken")
        assert "chicken" in result

        result = tools_inv.use_ingredient("chicken", 2.0)
        assert "已使用" in result or "✅" in result

    def test_restock(self):
        result = tools_inv.restock_ingredient("chicken", 5.0)
        assert "补货" in result


class TestBillingTools:
    """Test billing tools."""

    def test_bill_flow(self):
        # Add items to bill
        result = tools_billing.add_to_bill(3, "宫保鸡丁", 1, 68.0)
        assert "已添加" in result

        # Check bill
        result = tools_billing.get_bill(3)
        assert "¥68" in result or "宫保鸡丁" in result

        # Split
        result = tools_billing.split_bill(3, 2)
        assert "每人" in result

        # Pay
        result = tools_billing.pay_bill(3)
        assert "已支付" in result or "✅" in result
