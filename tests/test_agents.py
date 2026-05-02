"""单元测试 — 冰柜工具和Agent功能测试。"""

from app.db.memory import db
from app.models.schemas import OrderItem, DishSuggestion
from app.tools import fridge as tools_fridge
from app.tools import kitchen as tools_kitchen
from app.tools import inventory as tools_inv
from app.tools import billing as tools_billing


class TestFridgeTools:
    """冰柜展示核心功能"""

    def test_show_fridge_all(self):
        result = tools_fridge.show_fridge()
        assert "五花肉" in result
        assert "藜蒿" in result
        assert "腊肉" in result
        assert "冰柜" in result

    def test_show_fridge_category(self):
        result = tools_fridge.show_fridge("meat")
        assert "五花肉" in result
        assert "肉的" in result or "🥩" in result

        result = tools_fridge.show_fridge("vegetable")
        assert "辣椒" in result or "藜蒿" in result

    def test_show_fridge_item(self):
        result = tools_fridge.show_fridge_item(1)
        assert "五花肉" in result
        assert "价" in result

        result = tools_fridge.show_fridge_item(99)
        assert "没有" in result

    def test_search_fridge(self):
        result = tools_fridge.search_fridge("辣")
        assert "辣椒" in result

        result = tools_fridge.search_fridge("腊肉")
        assert "腊肉" in result

        result = tools_fridge.search_fridge("不存在的食材")
        assert "没找到" in result

    def test_suggest_dishes_classic(self):
        """经典赣菜搭配"""
        result = tools_fridge.suggest_dishes([11, 14])  # 腊肉+藜蒿
        assert "藜蒿炒腊肉" in result

        result = tools_fridge.suggest_dishes([1, 15])  # 五花肉+辣椒
        assert "辣椒炒肉" in result

    def test_suggest_dishes_single(self):
        """单一食材"""
        result = tools_fridge.suggest_dishes([1])  # 五花肉
        assert any(kw in result for kw in ["粉蒸肉", "红烧肉", "推荐"])

    def test_suggest_dishes_empty(self):
        """不存在的食材"""
        result = tools_fridge.suggest_dishes([99, 100])
        assert "没有" in result or "抱歉" in result


class TestKitchenTools:
    """厨房订单管理"""

    def test_create_and_process_order(self):
        result = tools_kitchen.create_order(5)
        assert "订单已创建" in result

        import re
        order_id = re.search(r"ORD-\w+", result).group()

        # Simulate adding a dish
        from app.db.memory import db
        order = db.get_order(order_id)
        assert order is not None

        item = OrderItem(dish_name="辣椒炒肉", ingredients_used=["五花肉", "辣椒"],
                         cooking_method="小炒", unit_price=35.0)
        db.add_order_item(order_id, item)

        # Confirm
        result = tools_kitchen.confirm_order(order_id)
        assert "已确认" in result

        # Start prep
        result = tools_kitchen.start_preparing(order_id)
        assert "开始制作" in result

        # Ready
        result = tools_kitchen.mark_order_ready(order_id)
        assert "已完成" in result


class TestInventoryTools:
    """库存管理"""

    def test_list_inventory(self):
        result = tools_inv.list_all_inventory()
        assert "五花肉" in result or "食材" in result

    def test_restock(self):
        result = tools_inv.restock_ingredient("五花肉", 5.0)
        assert "补货" in result or "✅" in result


class TestBillingTools:
    """账单测试"""

    def test_bill_flow(self):
        result = tools_billing.add_to_bill(3, "辣椒炒肉", 1, 35.0)
        assert "已添加" in result

        result = tools_billing.get_bill(3)
        assert "辣椒炒肉" in result

        result = tools_billing.split_bill(3, 2)
        assert "每人" in result or "均分" in result

        result = tools_billing.pay_bill(3)
        assert "已支付" in result or "✅" in result
