"""In-memory state store — serves as the restaurant's "database".

江西特色：没有菜单，全部食材摆冰柜，客人看着冰柜点菜。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.models.schemas import (
    Bill,
    BillItem,
    Conversation,
    CookingMethod,
    DishSuggestion,
    FridgeIngredient,
    Ingredient,
    IngredientCategory,
    Order,
    OrderItem,
    OrderStatus,
    Reservation,
    ReservationStatus,
    Table,
    TableStatus,
)


class RestaurantDB:
    """Thread-safe in-memory restaurant database."""

    def __init__(self) -> None:
        self.tables: dict[int, Table] = {}
        self.fridge: dict[int, FridgeIngredient] = {}   # 冰柜食材 (取代 menu)
        self.orders: dict[str, Order] = {}
        self.reservations: dict[str, Reservation] = {}
        self.inventory: dict[str, Ingredient] = {}
        self.bills: dict[int, Bill] = {}
        self.conversations: dict[str, Conversation] = {}
        self._init_defaults()

    # ── Default data ────────────────────────────────────

    def _init_defaults(self) -> None:
        # ── 桌位 ──
        tables = [
            Table(id=1, capacity=2, location="窗边"),
            Table(id=2, capacity=2, location="窗边"),
            Table(id=3, capacity=4, location="大厅"),
            Table(id=4, capacity=4, location="大厅"),
            Table(id=5, capacity=6, location="包间"),
            Table(id=6, capacity=8, location="包间"),
            Table(id=7, capacity=4, location="露台"),
            Table(id=8, capacity=2, location="露台"),
        ]
        for t in tables:
            self.tables[t.id] = t

        # ── 冰柜食材 (江西特色) ──
        # 肉类
        self._add_fridge(1, "Pork Belly", "五花肉", IngredientCategory.meat,
                         28.0, 5.0, "本地土猪，肥瘦相间",
                         [CookingMethod.stir_fry, CookingMethod.braise, CookingMethod.steam_with_rice_flour])
        self._add_fridge(2, "Pork Ribs", "排骨", IngredientCategory.meat,
                         38.0, 4.0, "土猪肋排",
                         [CookingMethod.stew, CookingMethod.braise, CookingMethod.steam_with_rice_flour])
        self._add_fridge(3, "Beef Brisket", "牛腩", IngredientCategory.meat,
                         48.0, 3.0, "赣南黄牛腩",
                         [CookingMethod.stew, CookingMethod.braise])
        self._add_fridge(4, "Beef Slices", "牛肉片", IngredientCategory.meat,
                         42.0, 2.5, "新鲜黄牛肉",
                         [CookingMethod.stir_fry, CookingMethod.boil])
        self._add_fridge(5, "Pork Liver", "猪肝", IngredientCategory.meat,
                         18.0, 2.0, "新鲜猪肝",
                         [CookingMethod.stir_fry])

        # 禽类
        self._add_fridge(6, "Local Chicken", "土鸡", IngredientCategory.poultry,
                         35.0, 3.0, "散养土鸡",
                         [CookingMethod.stew, CookingMethod.steam, CookingMethod.stir_fry])
        self._add_fridge(7, "Duck", "鸭", IngredientCategory.poultry,
                         25.0, 2.0, "鄱阳湖麻鸭",
                         [CookingMethod.braise, CookingMethod.stew, CookingMethod.smoke])

        # 水产
        self._add_fridge(8, "Grass Carp", "草鱼", IngredientCategory.seafood,
                         15.0, 4.0, "鄱阳湖草鱼",
                         [CookingMethod.stir_fry, CookingMethod.steam, CookingMethod.boil])
        self._add_fridge(9, "Crayfish", "小龙虾", IngredientCategory.seafood,
                         25.0, 10.0, "鄱阳湖清水小龙虾",
                         [CookingMethod.stir_fry, CookingMethod.braise])
        self._add_fridge(10, "River Shrimp", "河虾", IngredientCategory.seafood,
                         35.0, 1.5, "新鲜河虾",
                         [CookingMethod.stir_fry])

        # 腊味 (江西特色)
        self._add_fridge(11, "Cured Pork Belly", "腊肉", IngredientCategory.preserved,
                         45.0, 3.0, "赣南烟熏腊肉，柴火味十足",
                         [CookingMethod.stir_fry, CookingMethod.steam])
        self._add_fridge(12, "Cured Sausage", "腊肠", IngredientCategory.preserved,
                         38.0, 2.0, "手工灌制腊肠",
                         [CookingMethod.steam, CookingMethod.stir_fry])
        self._add_fridge(13, "Salted Duck", "板鸭", IngredientCategory.preserved,
                         30.0, 2.0, "南安板鸭，江西特产",
                         [CookingMethod.steam, CookingMethod.stir_fry])

        # 蔬菜
        self._add_fridge(14, "Artemisia Selengensis", "藜蒿", IngredientCategory.vegetable,
                         12.0, 2.0, "鄱阳湖野生藜蒿，江西名产",
                         [CookingMethod.stir_fry])
        self._add_fridge(15, "Chili Pepper", "辣椒", IngredientCategory.vegetable,
                         6.0, 5.0, "本地尖椒，辣味十足",
                         [CookingMethod.stir_fry])
        self._add_fridge(16, "Green Pepper", "青椒", IngredientCategory.vegetable,
                         5.0, 4.0, "新鲜青椒",
                         [CookingMethod.stir_fry])
        self._add_fridge(17, "Bamboo Shoots", "笋", IngredientCategory.vegetable,
                         10.0, 3.0, "井冈山春笋",
                         [CookingMethod.stir_fry, CookingMethod.boil])
        self._add_fridge(18, "Lotus Root", "莲藕", IngredientCategory.vegetable,
                         8.0, 4.0, "鄱阳湖莲藕，粉糯香甜",
                         [CookingMethod.stew, CookingMethod.stir_fry, CookingMethod.cold_mix])
        self._add_fridge(19, "Taro", "芋头", IngredientCategory.vegetable,
                         7.0, 3.0, "赣南芋头",
                         [CookingMethod.steam, CookingMethod.stew])
        self._add_fridge(20, "Chinese Chives", "韭菜", IngredientCategory.vegetable,
                         6.0, 2.0, "本地韭菜",
                         [CookingMethod.stir_fry])
        self._add_fridge(21, "Mushroom", "香菇", IngredientCategory.vegetable,
                         15.0, 2.0, "井冈山香菇",
                         [CookingMethod.stir_fry, CookingMethod.stew])
        self._add_fridge(22, "Preserved Vegetable", "腌菜", IngredientCategory.vegetable,
                         5.0, 3.0, "江西农家腌菜",
                         [CookingMethod.stir_fry])

        # 豆制品/蛋
        self._add_fridge(23, "Tofu", "豆腐", IngredientCategory.tofu_egg,
                         3.0, 3.0, "手工嫩豆腐",
                         [CookingMethod.stir_fry, CookingMethod.boil, CookingMethod.stew])
        self._add_fridge(24, "Pressed Tofu", "豆干", IngredientCategory.tofu_egg,
                         5.0, 2.0, "五香豆干",
                         [CookingMethod.stir_fry, CookingMethod.cold_mix])
        self._add_fridge(25, "Eggs", "鸡蛋", IngredientCategory.tofu_egg,
                         1.0, 5.0, "土鸡蛋",
                         [CookingMethod.stir_fry, CookingMethod.steam, CookingMethod.boil])

        # ── 厨房备货 ──
        for ing_name in ["五花肉", "排骨", "牛肉", "土鸡", "草鱼",
                          "腊肉", "辣椒", "藜蒿", "豆腐", "鸡蛋"]:
            self.inventory[ing_name] = Ingredient(name=ing_name, quantity_kg=5.0)

    def _add_fridge(
        self, fid: int, name: str, name_zh: str,
        category: IngredientCategory, price: float, qty: float,
        desc: str, methods: list[CookingMethod],
    ) -> None:
        self.fridge[fid] = FridgeIngredient(
            id=fid, name=name, name_zh=name_zh,
            category=category, price_per_500g=price,
            available_kg=qty, description=desc,
            suggested_methods=methods,
        )

    # ── 冰柜 (Fridge) 相关 ──────────────────────────────

    def get_fridge_display(self, category: IngredientCategory | None = None) -> list[FridgeIngredient]:
        """获取冰柜展示内容，可按类别筛选"""
        items = list(self.fridge.values())
        if category:
            items = [i for i in items if i.category == category]
        return items

    def get_fridge_item(self, fid: int) -> Optional[FridgeIngredient]:
        return self.fridge.get(fid)

    def search_fridge(self, keyword: str) -> list[FridgeIngredient]:
        """搜索冰柜里的食材"""
        kw = keyword.lower()
        return [
            i for i in self.fridge.values()
            if kw in i.name.lower() or kw in i.name_zh
        ]

    def suggest_dishes(self, ingredient_ids: list[int]) -> list[DishSuggestion]:
        """根据选中的冰柜食材，推荐江西做法"""
        selected = [self.fridge[i] for i in ingredient_ids if i in self.fridge]
        if not selected:
            return []

        suggestions: list[DishSuggestion] = []
        # 经典搭配库
        recipes = self._get_jiangxi_recipes()

        # 匹配可做的菜
        has = {s.name_zh for s in selected}
        for recipe in recipes:
            needed = set(recipe["main_ingredients"])
            if needed.issubset(has):
                suggestions.append(DishSuggestion(**recipe))

        # 按招牌优先排序
        suggestions.sort(key=lambda x: (not x.is_signature, x.estimated_price))
        return suggestions

    @staticmethod
    def _get_jiangxi_recipes() -> list[dict]:
        """赣菜经典搭配库"""
        return [
            # ── 经典赣菜 ──
            dict(name="Stir-fried Preserved Pork with Artemisia",
                 name_zh="藜蒿炒腊肉",
                 main_ingredients=["藜蒿", "腊肉"],
                 method=CookingMethod.stir_fry,
                 estimated_price=48, prep_time_minutes=15,
                 description="江西第一名菜！鄱阳湖野生藜蒿搭配赣南腊肉，清香爽脆",
                 is_signature=True),
            dict(name="Steamed Pork Belly with Rice Flour",
                 name_zh="粉蒸肉",
                 main_ingredients=["五花肉"],
                 method=CookingMethod.steam_with_rice_flour,
                 estimated_price=45, prep_time_minutes=40,
                 description="江西传统粉蒸肉，五花肉裹米粉蒸至酥烂",
                 is_signature=True),
            dict(name="Stir-fried Chili Pork",
                 name_zh="辣椒炒肉",
                 main_ingredients=["五花肉", "辣椒"],
                 method=CookingMethod.stir_fry,
                 estimated_price=35, prep_time_minutes=12,
                 description="江西家家户户都会做的家常菜，五花肉煸香配辣椒",
                 is_signature=True),
            dict(name="Stir-fried Beef with Chili",
                 name_zh="小炒黄牛肉",
                 main_ingredients=["牛肉片", "辣椒"],
                 method=CookingMethod.stir_fry,
                 estimated_price=48, prep_time_minutes=10,
                 description="大火快炒黄牛肉，嫩滑鲜辣"),
            dict(name="Stir-fried Pork Liver",
                 name_zh="爆炒猪肝",
                 main_ingredients=["猪肝", "辣椒", "韭菜"],
                 method=CookingMethod.stir_fry,
                 estimated_price=28, prep_time_minutes=8,
                 description="火候到位的爆炒猪肝，嫩而不腥"),
            dict(name="Braised Duck",
                 name_zh="红烧鸭",
                 main_ingredients=["鸭", "辣椒"],
                 method=CookingMethod.braise,
                 estimated_price=58, prep_time_minutes=35,
                 description="鄱阳湖麻鸭红烧，酱香浓郁"),
            dict(name="Stir-fried Crayfish",
                 name_zh="麻辣小龙虾",
                 main_ingredients=["小龙虾", "辣椒"],
                 method=CookingMethod.stir_fry,
                 estimated_price=68, prep_time_minutes=25,
                 description="鄱阳湖清水虾，麻辣鲜香，夜宵之王",
                 is_signature=True),
            # ── 汤品 ──
            dict(name="Clay Pot Pork Ribs Soup",
                 name_zh="瓦罐排骨汤",
                 main_ingredients=["排骨", "莲藕", "香菇"],
                 method=CookingMethod.stew,
                 estimated_price=38, prep_time_minutes=60,
                 description="江西瓦罐煨汤，慢火炖出骨汤精华",
                 is_signature=True),
            dict(name="Steamed Chicken Soup",
                 name_zh="土鸡汤",
                 main_ingredients=["土鸡", "香菇"],
                 method=CookingMethod.steam,
                 estimated_price=68, prep_time_minutes=90,
                 description="原盅隔水蒸土鸡，汤清味醇"),
            # ── 素菜/小菜 ──
            dict(name="Stir-fried Chives with Eggs",
                 name_zh="韭菜炒鸡蛋",
                 main_ingredients=["韭菜", "鸡蛋"],
                 method=CookingMethod.stir_fry,
                 estimated_price=18, prep_time_minutes=8,
                 description="简单家常菜，韭菜鲜嫩土鸡蛋香"),
            dict(name="Cold Mixed Tofu with Spring Onion",
                 name_zh="小葱拌豆腐",
                 main_ingredients=["豆腐"],
                 method=CookingMethod.cold_mix,
                 estimated_price=12, prep_time_minutes=5,
                 description="一清二白，清爽开胃"),
            dict(name="Stir-fried Preserved Vegetable with Pressed Tofu",
                 name_zh="腌菜炒豆干",
                 main_ingredients=["腌菜", "豆干", "辣椒"],
                 method=CookingMethod.stir_fry,
                 estimated_price=15, prep_time_minutes=8,
                 description="农家腌菜配五香豆干，下饭神器"),
            dict(name="Braised Pork Belly",
                 name_zh="红烧肉",
                 main_ingredients=["五花肉"],
                 method=CookingMethod.braise,
                 estimated_price=48, prep_time_minutes=50,
                 description="慢火红烧，肥而不腻"),
            dict(name="Steamed Taro with Chili Sauce",
                 name_zh="剁椒芋头",
                 main_ingredients=["芋头", "辣椒"],
                 method=CookingMethod.steam,
                 estimated_price=22, prep_time_minutes=20,
                 description="芋头软糯，剁椒提味"),
            dict(name="Stir-fried Bamboo Shoots with Preserved Pork",
                 name_zh="笋炒腊肉",
                 main_ingredients=["笋", "腊肉"],
                 method=CookingMethod.stir_fry,
                 estimated_price=38, prep_time_minutes=15,
                 description="井冈山春笋炒腊肉，春天的味道"),
            dict(name="Fish Head with Chili",
                 name_zh="剁椒鱼头",
                 main_ingredients=["草鱼", "辣椒"],
                 method=CookingMethod.steam,
                 estimated_price=58, prep_time_minutes=25,
                 description="鲜辣过瘾的剁椒蒸鱼头"),
        ]

    # ── Tables ──────────────────────────────────────────

    def get_available_tables(self, capacity: int) -> list[Table]:
        return [t for t in self.tables.values()
                if t.status == TableStatus.available and t.capacity >= capacity]

    def get_table(self, table_id: int) -> Optional[Table]:
        return self.tables.get(table_id)

    def occupy_table(self, table_id: int) -> bool:
        t = self.tables.get(table_id)
        if t and t.status == TableStatus.available:
            t.status = TableStatus.occupied
            return True
        return False

    def free_table(self, table_id: int) -> bool:
        t = self.tables.get(table_id)
        if t and t.status == TableStatus.occupied:
            t.status = TableStatus.available
            return True
        return False

    # ── Orders ──────────────────────────────────────────

    def create_order(self, table_id: int, customer_name: str = "") -> Order:
        oid = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        order = Order(id=oid, table_id=table_id, customer_name=customer_name)
        self.orders[oid] = order
        return order

    def add_order_item(self, order_id: str, item: OrderItem) -> Optional[Order]:
        order = self.orders.get(order_id)
        if not order:
            return None
        order.items.append(item)
        order.total = sum(i.unit_price * i.quantity for i in order.items)
        return order

    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        order = self.orders.get(order_id)
        if order:
            order.status = status
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    def get_orders_for_table(self, table_id: int) -> list[Order]:
        return [o for o in self.orders.values() if o.table_id == table_id]

    # ── Reservations ────────────────────────────────────

    def create_reservation(
        self, customer: str, phone: str, party_size: int,
        time: datetime, table_id: int | None = None,
        special_requests: str = "",
    ) -> Reservation:
        rid = f"RES-{uuid.uuid4().hex[:8].upper()}"
        res = Reservation(
            id=rid, customer_name=customer, phone=phone,
            party_size=party_size, time=time, table_id=table_id,
            special_requests=special_requests,
        )
        self.reservations[rid] = res
        if table_id and table_id in self.tables:
            self.tables[table_id].status = TableStatus.reserved
        return res

    def cancel_reservation(self, res_id: str) -> bool:
        res = self.reservations.get(res_id)
        if not res:
            return False
        res.status = ReservationStatus.cancelled
        if res.table_id and res.table_id in self.tables:
            self.tables[res.table_id].status = TableStatus.available
        return True

    def get_reservation(self, res_id: str) -> Optional[Reservation]:
        return self.reservations.get(res_id)

    def list_reservations(self) -> list[Reservation]:
        return list(self.reservations.values())

    # ── Inventory ───────────────────────────────────────

    def check_inventory(self, ingredient: str) -> Optional[Ingredient]:
        return self.inventory.get(ingredient)

    def use_ingredient(self, name: str, qty_kg: float) -> bool:
        ing = self.inventory.get(name)
        if ing and ing.quantity_kg >= qty_kg:
            ing.quantity_kg -= qty_kg
            return True
        return False

    def restock(self, name: str, qty_kg: float) -> Optional[Ingredient]:
        ing = self.inventory.get(name)
        if ing:
            ing.quantity_kg += qty_kg
        return ing

    def list_inventory(self) -> list[Ingredient]:
        return list(self.inventory.values())

    # ── Bills ───────────────────────────────────────────

    def get_or_create_bill(self, table_id: int) -> Bill:
        if table_id not in self.bills:
            self.bills[table_id] = Bill(table_id=table_id)
        return self.bills[table_id]

    def add_to_bill(self, table_id: int, items: list[BillItem]) -> Bill:
        bill = self.get_or_create_bill(table_id)
        bill.items.extend(items)
        bill.subtotal = sum(i.unit_price * i.quantity for i in bill.items)
        bill.service_charge = round(bill.subtotal * 0.10, 2)
        bill.tax = round(bill.subtotal * 0.06, 2)
        bill.total = round(bill.subtotal + bill.service_charge + bill.tax, 2)
        return bill

    def pay_bill(self, table_id: int) -> Optional[Bill]:
        bill = self.bills.get(table_id)
        if bill:
            bill.paid = True
        return bill

    # ── Conversations ───────────────────────────────────

    def get_or_create_conversation(self, session_id: str) -> Conversation:
        if session_id not in self.conversations:
            self.conversations[session_id] = Conversation(session_id=session_id)
        return self.conversations[session_id]

    def add_turn(self, conv: Conversation, role: str, message: str, agent: str = "supervisor") -> None:
        from app.models.schemas import AgentType, ConversationTurn
        conv.turns.append(ConversationTurn(
            role=role, message=message,
            agent=AgentType(agent) if agent in [e.value for e in AgentType] else AgentType.supervisor,
        ))


# Singleton
db = RestaurantDB()
