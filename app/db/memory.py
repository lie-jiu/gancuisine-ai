"""In-memory state store — serves as the restaurant's "database"."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.models.schemas import (
    Bill,
    BillItem,
    Conversation,
    Ingredient,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Reservation,
    ReservationStatus,
    Table,
    TableStatus,
)


class RestaurantDB:
    """Thread-safe (single-threaded asyncio) in-memory store."""

    def __init__(self) -> None:
        self.tables: dict[int, Table] = {}
        self.menu: dict[int, MenuItem] = {}
        self.orders: dict[str, Order] = {}
        self.reservations: dict[str, Reservation] = {}
        self.inventory: dict[str, Ingredient] = {}
        self.bills: dict[int, Bill] = {}
        self.conversations: dict[str, Conversation] = {}
        self._init_defaults()

    # ── Default data ────────────────────────────────────

    def _init_defaults(self) -> None:
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

        menu_items = [
            MenuItem(id=1, name="Kung Pao Chicken", name_zh="宫保鸡丁",
                     category="main", price=68.00, prep_time_minutes=18,
                     ingredients=["chicken", "peanuts", "chili", "scallion"]),
            MenuItem(id=2, name="Mapo Tofu", name_zh="麻婆豆腐",
                     category="main", price=48.00, prep_time_minutes=15,
                     ingredients=["tofu", "pork mince", "doubanjiang", "Sichuan pepper"]),
            MenuItem(id=3, name="Spring Rolls (6pcs)", name_zh="春卷",
                     category="appetizer", price=32.00, prep_time_minutes=12,
                     ingredients=["spring roll wrapper", "vegetables", "mushroom"]),
            MenuItem(id=4, name="Peking Duck", name_zh="北京烤鸭",
                     category="main", price=168.00, prep_time_minutes=45,
                     ingredients=["duck", "pancake", "hoisin sauce", "cucumber"]),
            MenuItem(id=5, name="Fried Rice", name_zh="蛋炒饭",
                     category="main", price=38.00, prep_time_minutes=10,
                     ingredients=["rice", "egg", "scallion", "soy sauce"]),
            MenuItem(id=6, name="Wonton Soup", name_zh="馄饨汤",
                     category="appetizer", price=28.00, prep_time_minutes=12,
                     ingredients=["wonton wrapper", "pork", "shrimp", "broth"]),
            MenuItem(id=7, name="Chocolate Mousse", name_zh="巧克力慕斯",
                     category="dessert", price=42.00, prep_time_minutes=5,
                     ingredients=["chocolate", "cream", "egg", "sugar"]),
            MenuItem(id=8, name="Green Tea Ice Cream", name_zh="抹茶冰淇淋",
                     category="dessert", price=28.00, prep_time_minutes=3,
                     ingredients=["matcha", "cream", "milk", "sugar"]),
            MenuItem(id=9, name="Jasmine Tea", name_zh="茉莉花茶",
                     category="drink", price=18.00, prep_time_minutes=3,
                     ingredients=["jasmine green tea", "hot water"]),
            MenuItem(id=10, name="House Red Wine (glass)", name_zh="红酒（杯）",
                     category="wine", price=58.00, prep_time_minutes=2,
                     ingredients=["cabernet sauvignon"]),
            MenuItem(id=11, name="House White Wine (glass)", name_zh="白葡萄酒（杯）",
                     category="wine", price=58.00, prep_time_minutes=2,
                     ingredients=["sauvignon blanc"]),
            MenuItem(id=12, name="Chinese Baijiu Moutai (shot)", name_zh="茅台（杯）",
                     category="wine", price=168.00, prep_time_minutes=1,
                     ingredients=["maotai liquor"]),
        ]
        for m in menu_items:
            self.menu[m.id] = m

        inventory_data = [
            Ingredient(name="chicken", quantity=10.0, unit="kg", min_threshold=2.0),
            Ingredient(name="tofu", quantity=5.0, unit="kg", min_threshold=1.0),
            Ingredient(name="duck", quantity=3.0, unit="kg", min_threshold=1.0),
            Ingredient(name="rice", quantity=20.0, unit="kg", min_threshold=5.0),
            Ingredient(name="shrimp", quantity=4.0, unit="kg", min_threshold=1.0),
            Ingredient(name="vegetables", quantity=8.0, unit="kg", min_threshold=2.0),
            Ingredient(name="chocolate", quantity=3.0, unit="kg", min_threshold=0.5),
            Ingredient(name="matcha", quantity=2.0, unit="kg", min_threshold=0.5),
        ]
        for ing in inventory_data:
            self.inventory[ing.name] = ing

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

    # ── Menu ────────────────────────────────────────────

    def get_menu(self, category: str | None = None) -> list[MenuItem]:
        items = [m for m in self.menu.values() if m.available]
        if category:
            items = [m for m in items if m.category == category]
        return items

    def get_menu_item(self, item_id: int) -> Optional[MenuItem]:
        return self.menu.get(item_id)

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
        # recalc total
        menu_item = self.menu.get(item.menu_item_id)
        if menu_item:
            item.menu_item_name = menu_item.name_zh
            order.total = sum(
                self.menu.get(i.menu_item_id, MenuItem(id=0, name="?", name_zh="?", category="?", price=0)).price * i.quantity
                for i in order.items
            )
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

    def use_ingredient(self, name: str, qty: float) -> bool:
        ing = self.inventory.get(name)
        if ing and ing.quantity >= qty:
            ing.quantity -= qty
            return True
        return False

    def restock(self, name: str, qty: float) -> Optional[Ingredient]:
        ing = self.inventory.get(name)
        if ing:
            ing.quantity += qty
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
            agent=AgentType(agent) if agent in AgentType._value2member_map_ else AgentType.supervisor,
        ))


# Singleton
db = RestaurantDB()
