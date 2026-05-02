"""SQLite-backed restaurant database — persistent, same interface as RestaurantDB.

数据存储位置：data/restaurant.db（项目根目录下）
首次运行时自动建表 + 导入种子数据。
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.schemas import (
    Bill,
    BillItem,
    Conversation,
    ConversationTurn,
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

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "restaurant.db"


def _get_db() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ──────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fridge_ingredients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    name_zh TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    price_per_500g REAL NOT NULL DEFAULT 0.0,
    available_kg REAL NOT NULL DEFAULT 0.0,
    description TEXT NOT NULL DEFAULT '',
    season TEXT NOT NULL DEFAULT '全年',
    suggested_methods TEXT NOT NULL DEFAULT '[]',
    image_url TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS restaurant_tables (
    id INTEGER PRIMARY KEY,
    capacity INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    location TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    table_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    total REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    dish_name TEXT NOT NULL DEFAULT '',
    ingredients_used TEXT NOT NULL DEFAULT '[]',
    cooking_method TEXT NOT NULL DEFAULT '小炒',
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0.0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservations (
    id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    party_size INTEGER NOT NULL,
    time TEXT NOT NULL,
    table_id INTEGER,
    status TEXT NOT NULL DEFAULT 'confirmed',
    special_requests TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    name TEXT PRIMARY KEY,
    quantity_kg REAL NOT NULL DEFAULT 0.0,
    unit TEXT NOT NULL DEFAULT '斤',
    min_threshold REAL NOT NULL DEFAULT 2.0
);

CREATE TABLE IF NOT EXISTS bills (
    table_id INTEGER PRIMARY KEY,
    subtotal REAL NOT NULL DEFAULT 0.0,
    service_charge REAL NOT NULL DEFAULT 0.0,
    tax REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    paid INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bill_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL REFERENCES bills(table_id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS conversations (
    session_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL DEFAULT '',
    active_order_id TEXT,
    active_reservation_id TEXT
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT 'supervisor',
    timestamp TEXT NOT NULL
);
"""


# ── Seed data helper (same as memory.py) ─────────────────────────────────

def _seed_data(conn: sqlite3.Connection) -> None:
    """Populate fridge, tables, and inventory with default Jiangxi data."""
    existing = conn.execute("SELECT COUNT(*) FROM fridge_ingredients").fetchone()[0]
    if existing > 0:
        return  # already seeded

    # ── Tables ──
    tables = [
        (1, 2, "available", "窗边"),
        (2, 2, "available", "窗边"),
        (3, 4, "available", "大厅"),
        (4, 4, "available", "大厅"),
        (5, 6, "available", "包间"),
        (6, 8, "available", "包间"),
        (7, 4, "available", "露台"),
        (8, 2, "available", "露台"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO restaurant_tables (id, capacity, status, location) VALUES (?,?,?,?)",
        tables,
    )

    # ── Fridge ingredients ──
    fridge_data: list[tuple] = [
        (1, "Pork Belly", "五花肉", "meat", 28.0, 5.0, "本地土猪，肥瘦相间",
         json.dumps(["小炒", "红烧", "粉蒸"], ensure_ascii=False)),
        (2, "Pork Ribs", "排骨", "meat", 38.0, 4.0, "土猪肋排",
         json.dumps(["炖", "红烧", "粉蒸"], ensure_ascii=False)),
        (3, "Beef Brisket", "牛腩", "meat", 48.0, 3.0, "赣南黄牛腩",
         json.dumps(["炖", "红烧"], ensure_ascii=False)),
        (4, "Beef Slices", "牛肉片", "meat", 42.0, 2.5, "新鲜黄牛肉",
         json.dumps(["小炒", "煮"], ensure_ascii=False)),
        (5, "Pork Liver", "猪肝", "meat", 18.0, 2.0, "新鲜猪肝",
         json.dumps(["小炒"], ensure_ascii=False)),
        (6, "Local Chicken", "土鸡", "poultry", 35.0, 3.0, "散养土鸡",
         json.dumps(["炖", "清蒸", "小炒"], ensure_ascii=False)),
        (7, "Duck", "鸭", "poultry", 25.0, 2.0, "鄱阳湖麻鸭",
         json.dumps(["红烧", "炖", "烟熏"], ensure_ascii=False)),
        (8, "Grass Carp", "草鱼", "seafood", 15.0, 4.0, "鄱阳湖草鱼",
         json.dumps(["小炒", "清蒸", "煮"], ensure_ascii=False)),
        (9, "Crayfish", "小龙虾", "seafood", 25.0, 10.0, "鄱阳湖清水小龙虾",
         json.dumps(["小炒", "红烧"], ensure_ascii=False)),
        (10, "River Shrimp", "河虾", "seafood", 35.0, 1.5, "新鲜河虾",
         json.dumps(["小炒"], ensure_ascii=False)),
        (11, "Cured Pork Belly", "腊肉", "preserved", 45.0, 3.0, "赣南烟熏腊肉，柴火味十足",
         json.dumps(["小炒", "清蒸"], ensure_ascii=False)),
        (12, "Cured Sausage", "腊肠", "preserved", 38.0, 2.0, "手工灌制腊肠",
         json.dumps(["清蒸", "小炒"], ensure_ascii=False)),
        (13, "Salted Duck", "板鸭", "preserved", 30.0, 2.0, "南安板鸭，江西特产",
         json.dumps(["清蒸", "小炒"], ensure_ascii=False)),
        (14, "Artemisia Selengensis", "藜蒿", "vegetable", 12.0, 2.0, "鄱阳湖野生藜蒿，江西名产",
         json.dumps(["小炒"], ensure_ascii=False)),
        (15, "Chili Pepper", "辣椒", "vegetable", 6.0, 5.0, "本地尖椒，辣味十足",
         json.dumps(["小炒"], ensure_ascii=False)),
        (16, "Green Pepper", "青椒", "vegetable", 5.0, 4.0, "新鲜青椒",
         json.dumps(["小炒"], ensure_ascii=False)),
        (17, "Bamboo Shoots", "笋", "vegetable", 10.0, 3.0, "井冈山春笋",
         json.dumps(["小炒", "煮"], ensure_ascii=False)),
        (18, "Lotus Root", "莲藕", "vegetable", 8.0, 4.0, "鄱阳湖莲藕，粉糯香甜",
         json.dumps(["炖", "小炒", "凉拌"], ensure_ascii=False)),
        (19, "Taro", "芋头", "vegetable", 7.0, 3.0, "赣南芋头",
         json.dumps(["清蒸", "炖"], ensure_ascii=False)),
        (20, "Chinese Chives", "韭菜", "vegetable", 6.0, 2.0, "本地韭菜",
         json.dumps(["小炒"], ensure_ascii=False)),
        (21, "Mushroom", "香菇", "vegetable", 15.0, 2.0, "井冈山香菇",
         json.dumps(["小炒", "炖"], ensure_ascii=False)),
        (22, "Preserved Vegetable", "腌菜", "vegetable", 5.0, 3.0, "江西农家腌菜",
         json.dumps(["小炒"], ensure_ascii=False)),
        (23, "Tofu", "豆腐", "tofu_egg", 3.0, 3.0, "手工嫩豆腐",
         json.dumps(["小炒", "煮", "炖"], ensure_ascii=False)),
        (24, "Pressed Tofu", "豆干", "tofu_egg", 5.0, 2.0, "五香豆干",
         json.dumps(["小炒", "凉拌"], ensure_ascii=False)),
        (25, "Eggs", "鸡蛋", "tofu_egg", 1.0, 5.0, "土鸡蛋",
         json.dumps(["小炒", "清蒸", "煮"], ensure_ascii=False)),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO fridge_ingredients
           (id, name, name_zh, category, price_per_500g, available_kg,
            description, suggested_methods)
           VALUES (?,?,?,?,?,?,?,?)""",
        fridge_data,
    )

    # ── Inventory ──
    inv_names = ["五花肉", "排骨", "牛肉", "土鸡", "草鱼",
                 "腊肉", "辣椒", "藜蒿", "豆腐", "鸡蛋"]
    conn.executemany(
        "INSERT OR IGNORE INTO inventory (name, quantity_kg, unit, min_threshold) VALUES (?,?,?,?)",
        [(n, 5.0, "斤", 2.0) for n in inv_names],
    )
    conn.commit()


# ── Helpers ─────────────────────────────────────────────────────────────

def _row_to_table(r: sqlite3.Row) -> Table:
    return Table(id=r["id"], capacity=r["capacity"],
                 status=TableStatus(r["status"]), location=r["location"])


def _row_to_fridge(r: sqlite3.Row) -> FridgeIngredient:
    methods = [CookingMethod(m) for m in json.loads(r["suggested_methods"])]
    return FridgeIngredient(
        id=r["id"], name=r["name"], name_zh=r["name_zh"],
        category=IngredientCategory(r["category"]),
        price_per_500g=r["price_per_500g"], available_kg=r["available_kg"],
        description=r["description"], season=r["season"],
        suggested_methods=methods, image_url=r["image_url"],
    )


def _row_to_order_item(r: sqlite3.Row) -> OrderItem:
    return OrderItem(
        dish_name=r["dish_name"],
        ingredients_used=json.loads(r["ingredients_used"]),
        cooking_method=r["cooking_method"],
        quantity=r["quantity"], unit_price=r["unit_price"],
        notes=r["notes"],
    )


def _row_to_order(r: sqlite3.Row, items: list[OrderItem]) -> Order:
    return Order(
        id=r["id"], table_id=r["table_id"],
        customer_name=r["customer_name"],
        status=OrderStatus(r["status"]),
        created_at=datetime.fromisoformat(r["created_at"]),
        total=r["total"], items=items,
    )


def _row_to_reservation(r: sqlite3.Row) -> Reservation:
    return Reservation(
        id=r["id"], customer_name=r["customer_name"],
        phone=r["phone"], party_size=r["party_size"],
        time=datetime.fromisoformat(r["time"]),
        table_id=r["table_id"], status=ReservationStatus(r["status"]),
        special_requests=r["special_requests"],
        created_at=datetime.fromisoformat(r["created_at"]),
    )


def _row_to_inventory(r: sqlite3.Row) -> Ingredient:
    return Ingredient(
        name=r["name"], quantity_kg=r["quantity_kg"],
        unit=r["unit"], min_threshold=r["min_threshold"],
    )


def _row_to_bill(r: sqlite3.Row, items: list[BillItem]) -> Bill:
    return Bill(
        table_id=r["table_id"],
        items=items, subtotal=r["subtotal"],
        service_charge=r["service_charge"],
        tax=r["tax"], total=r["total"],
        paid=bool(r["paid"]),
    )


def _row_to_bill_item(r: sqlite3.Row) -> BillItem:
    return BillItem(
        description=r["description"],
        quantity=r["quantity"], unit_price=r["unit_price"],
    )


JX_RECIPES: list[dict] = [
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


# ── SqliteRestaurantDB ─────────────────────────────────────────────────

class SqliteRestaurantDB:
    """SQLite-backed restaurant database — same API as RestaurantDB."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        try:
            for stmt in SCHEMA_SQL.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(s)
            _seed_data(conn)
        finally:
            conn.close()

    # ── Tables ──

    def get_available_tables(self, capacity: int) -> list[Table]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM restaurant_tables WHERE status=? AND capacity>=?",
                (TableStatus.available.value, capacity),
            ).fetchall()
            return [_row_to_table(r) for r in rows]
        finally:
            conn.close()

    def get_table(self, table_id: int) -> Optional[Table]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM restaurant_tables WHERE id=?", (table_id,)
            ).fetchone()
            return _row_to_table(r) if r else None
        finally:
            conn.close()

    def occupy_table(self, table_id: int) -> bool:
        conn = self._get_conn()
        try:
            t = conn.execute(
                "SELECT * FROM restaurant_tables WHERE id=? AND status=?",
                (table_id, TableStatus.available.value),
            ).fetchone()
            if not t:
                return False
            conn.execute(
                "UPDATE restaurant_tables SET status=? WHERE id=?",
                (TableStatus.occupied.value, table_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def free_table(self, table_id: int) -> bool:
        conn = self._get_conn()
        try:
            t = conn.execute(
                "SELECT * FROM restaurant_tables WHERE id=? AND status=?",
                (table_id, TableStatus.occupied.value),
            ).fetchone()
            if not t:
                return False
            conn.execute(
                "UPDATE restaurant_tables SET status=? WHERE id=?",
                (TableStatus.available.value, table_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ── Fridge ──

    def get_fridge_display(self, category: IngredientCategory | None = None) -> list[FridgeIngredient]:
        conn = self._get_conn()
        try:
            if category:
                rows = conn.execute(
                    "SELECT * FROM fridge_ingredients WHERE category=? ORDER BY id",
                    (category.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM fridge_ingredients ORDER BY id"
                ).fetchall()
            return [_row_to_fridge(r) for r in rows]
        finally:
            conn.close()

    def get_fridge_item(self, fid: int) -> Optional[FridgeIngredient]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM fridge_ingredients WHERE id=?", (fid,)
            ).fetchone()
            return _row_to_fridge(r) if r else None
        finally:
            conn.close()

    def search_fridge(self, keyword: str) -> list[FridgeIngredient]:
        conn = self._get_conn()
        try:
            like = f"%{keyword}%"
            rows = conn.execute(
                "SELECT * FROM fridge_ingredients WHERE name LIKE ? OR name_zh LIKE ? ORDER BY id",
                (like, like),
            ).fetchall()
            return [_row_to_fridge(r) for r in rows]
        finally:
            conn.close()

    def suggest_dishes(self, ingredient_ids: list[int]) -> list[DishSuggestion]:
        conn = self._get_conn()
        try:
            if not ingredient_ids:
                return []
            placeholders = ",".join("?" for _ in ingredient_ids)
            rows = conn.execute(
                f"SELECT name_zh FROM fridge_ingredients WHERE id IN ({placeholders})",
                ingredient_ids,
            ).fetchall()
            has = {r["name_zh"] for r in rows}

            suggestions: list[DishSuggestion] = []
            for recipe in JX_RECIPES:
                needed = set(recipe["main_ingredients"])
                if needed.issubset(has):
                    suggestions.append(DishSuggestion(**recipe))

            suggestions.sort(key=lambda x: (not x.is_signature, x.estimated_price))
            return suggestions
        finally:
            conn.close()

    # ── Orders ──

    def create_order(self, table_id: int, customer_name: str = "") -> Order:
        conn = self._get_conn()
        try:
            oid = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO orders (id, table_id, customer_name, status, created_at, total) VALUES (?,?,?,?,?,0.0)",
                (oid, table_id, customer_name, OrderStatus.pending.value, now),
            )
            conn.commit()
            return Order(id=oid, table_id=table_id, customer_name=customer_name,
                         created_at=datetime.fromisoformat(now))
        finally:
            conn.close()

    def add_order_item(self, order_id: str, item: OrderItem) -> Optional[Order]:
        conn = self._get_conn()
        try:
            # Check order exists
            r = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not r:
                return None

            # Insert item
            conn.execute(
                """INSERT INTO order_items
                   (order_id, dish_name, ingredients_used, cooking_method,
                    quantity, unit_price, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (order_id, item.dish_name,
                 json.dumps(item.ingredients_used, ensure_ascii=False),
                 item.cooking_method, item.quantity,
                 item.unit_price, item.notes),
            )
            # Recalculate total
            row = conn.execute(
                "SELECT SUM(unit_price * quantity) as total FROM order_items WHERE order_id=?",
                (order_id,),
            ).fetchone()
            new_total = row["total"] or 0.0
            conn.execute("UPDATE orders SET total=? WHERE id=?", (new_total, order_id))
            conn.commit()

            return self.get_order(order_id)
        finally:
            conn.close()

    def update_order_status(self, order_id: str, status: OrderStatus) -> Optional[Order]:
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE orders SET status=? WHERE id=?",
                (status.value, order_id),
            )
            conn.commit()
            return self.get_order(order_id)
        finally:
            conn.close()

    def get_order(self, order_id: str) -> Optional[Order]:
        conn = self._get_conn()
        try:
            r = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not r:
                return None
            item_rows = conn.execute(
                "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
                (order_id,),
            ).fetchall()
            items = [_row_to_order_item(ir) for ir in item_rows]
            return _row_to_order(r, items)
        finally:
            conn.close()

    def get_orders_for_table(self, table_id: int) -> list[Order]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM orders WHERE table_id=? ORDER BY created_at DESC",
                (table_id,),
            ).fetchall()
            orders: list[Order] = []
            for r in rows:
                item_rows = conn.execute(
                    "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
                    (r["id"],),
                ).fetchall()
                items = [_row_to_order_item(ir) for ir in item_rows]
                orders.append(_row_to_order(r, items))
            return orders
        finally:
            conn.close()

    # ── Reservations ──

    def create_reservation(
        self, customer: str, phone: str, party_size: int,
        time: datetime, table_id: int | None = None,
        special_requests: str = "",
    ) -> Reservation:
        conn = self._get_conn()
        try:
            rid = f"RES-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO reservations
                   (id, customer_name, phone, party_size, time, table_id,
                    status, special_requests, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (rid, customer, phone, party_size, time.isoformat(),
                 table_id, ReservationStatus.confirmed.value,
                 special_requests, now),
            )
            if table_id:
                t = conn.execute(
                    "SELECT * FROM restaurant_tables WHERE id=?",
                    (table_id,),
                ).fetchone()
                if t and t["status"] == TableStatus.available.value:
                    conn.execute(
                        "UPDATE restaurant_tables SET status=? WHERE id=?",
                        (TableStatus.reserved.value, table_id),
                    )
            conn.commit()
            return Reservation(
                id=rid, customer_name=customer, phone=phone,
                party_size=party_size, time=time, table_id=table_id,
                special_requests=special_requests,
                created_at=datetime.fromisoformat(now),
            )
        finally:
            conn.close()

    def cancel_reservation(self, res_id: str) -> bool:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM reservations WHERE id=?", (res_id,),
            ).fetchone()
            if not r:
                return False
            conn.execute(
                "UPDATE reservations SET status=? WHERE id=?",
                (ReservationStatus.cancelled.value, res_id),
            )
            if r["table_id"]:
                conn.execute(
                    "UPDATE restaurant_tables SET status=? WHERE id=?",
                    (TableStatus.available.value, r["table_id"]),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_reservation(self, res_id: str) -> Optional[Reservation]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM reservations WHERE id=?", (res_id,),
            ).fetchone()
            return _row_to_reservation(r) if r else None
        finally:
            conn.close()

    def list_reservations(self) -> list[Reservation]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM reservations ORDER BY time"
            ).fetchall()
            return [_row_to_reservation(r) for r in rows]
        finally:
            conn.close()

    # ── Inventory ──

    def check_inventory(self, ingredient: str) -> Optional[Ingredient]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM inventory WHERE name=?", (ingredient,),
            ).fetchone()
            return _row_to_inventory(r) if r else None
        finally:
            conn.close()

    def use_ingredient(self, name: str, qty_kg: float) -> bool:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM inventory WHERE name=? AND quantity_kg>=?",
                (name, qty_kg),
            ).fetchone()
            if not r:
                return False
            conn.execute(
                "UPDATE inventory SET quantity_kg=quantity_kg-? WHERE name=?",
                (qty_kg, name),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def restock(self, name: str, qty_kg: float) -> Optional[Ingredient]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM inventory WHERE name=?", (name,),
            ).fetchone()
            if not r:
                return None
            conn.execute(
                "UPDATE inventory SET quantity_kg=quantity_kg+? WHERE name=?",
                (qty_kg, name),
            )
            conn.commit()
            r = conn.execute(
                "SELECT * FROM inventory WHERE name=?", (name,),
            ).fetchone()
            return _row_to_inventory(r)
        finally:
            conn.close()

    def list_inventory(self) -> list[Ingredient]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
            return [_row_to_inventory(r) for r in rows]
        finally:
            conn.close()

    # ── Bills ──

    def get_or_create_bill(self, table_id: int) -> Bill:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM bills WHERE table_id=?", (table_id,),
            ).fetchone()
            if r:
                item_rows = conn.execute(
                    "SELECT * FROM bill_items WHERE table_id=? ORDER BY id",
                    (table_id,),
                ).fetchall()
                items = [_row_to_bill_item(ir) for ir in item_rows]
                return _row_to_bill(r, items)

            conn.execute(
                "INSERT INTO bills (table_id) VALUES (?)", (table_id,),
            )
            conn.commit()
            return Bill(table_id=table_id)
        finally:
            conn.close()

    def add_to_bill(self, table_id: int, items: list[BillItem]) -> Bill:
        conn = self._get_conn()
        try:
            # Ensure bill exists
            self.get_or_create_bill(table_id)

            for item in items:
                conn.execute(
                    "INSERT INTO bill_items (table_id, description, quantity, unit_price) VALUES (?,?,?,?)",
                    (table_id, item.description, item.quantity, item.unit_price),
                )

            # Recalculate
            row = conn.execute(
                "SELECT SUM(unit_price * quantity) as subtotal FROM bill_items WHERE table_id=?",
                (table_id,),
            ).fetchone()
            subtotal = row["subtotal"] or 0.0
            service_charge = round(subtotal * 0.10, 2)
            tax = round(subtotal * 0.06, 2)
            total = round(subtotal + service_charge + tax, 2)
            conn.execute(
                "UPDATE bills SET subtotal=?, service_charge=?, tax=?, total=? WHERE table_id=?",
                (subtotal, service_charge, tax, total, table_id),
            )
            conn.commit()

            item_rows = conn.execute(
                "SELECT * FROM bill_items WHERE table_id=? ORDER BY id",
                (table_id,),
            ).fetchall()
            return _row_to_bill(
                conn.execute("SELECT * FROM bills WHERE table_id=?", (table_id,)).fetchone(),
                [_row_to_bill_item(ir) for ir in item_rows],
            )
        finally:
            conn.close()

    def pay_bill(self, table_id: int) -> Optional[Bill]:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM bills WHERE table_id=?", (table_id,),
            ).fetchone()
            if not r:
                return None
            conn.execute(
                "UPDATE bills SET paid=1 WHERE table_id=?", (table_id,),
            )
            conn.commit()
            item_rows = conn.execute(
                "SELECT * FROM bill_items WHERE table_id=? ORDER BY id",
                (table_id,),
            ).fetchall()
            return _row_to_bill(
                conn.execute("SELECT * FROM bills WHERE table_id=?", (table_id,)).fetchone(),
                [_row_to_bill_item(ir) for ir in item_rows],
            )
        finally:
            conn.close()

    # ── Conversations ──

    def get_or_create_conversation(self, session_id: str) -> Conversation:
        conn = self._get_conn()
        try:
            r = conn.execute(
                "SELECT * FROM conversations WHERE session_id=?", (session_id,),
            ).fetchone()
            if r:
                turn_rows = conn.execute(
                    "SELECT * FROM conversation_turns WHERE session_id=? ORDER BY id",
                    (session_id,),
                ).fetchall()
                turns = [
                    ConversationTurn(
                        role=t["role"], message=t["message"],
                        agent=t["agent"],
                        timestamp=datetime.fromisoformat(t["timestamp"]),
                    )
                    for t in turn_rows
                ]
                return Conversation(
                    session_id=session_id, customer_name=r["customer_name"],
                    active_order_id=r["active_order_id"],
                    active_reservation_id=r["active_reservation_id"],
                    turns=turns,
                )

            conn.execute(
                "INSERT INTO conversations (session_id) VALUES (?)", (session_id,),
            )
            conn.commit()
            return Conversation(session_id=session_id)
        finally:
            conn.close()

    def add_turn(self, conv: Conversation, role: str, message: str, agent: str = "supervisor") -> None:
        conn = self._get_conn()
        try:
            from app.models.schemas import AgentType

            agent_val = agent if agent in [e.value for e in AgentType] else "supervisor"
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO conversation_turns (session_id, role, message, agent, timestamp) VALUES (?,?,?,?,?)",
                (conv.session_id, role, message, agent_val, now),
            )
            conn.commit()

            conv.turns.append(ConversationTurn(
                role=role, message=message,
                agent=AgentType(agent_val),
                timestamp=datetime.fromisoformat(now),
            ))
        finally:
            conn.close()

    # ── Cleanup helper for testing ──

    def reset_db(self) -> None:
        """Drop all data and re-initialize (for testing)."""
        conn = self._get_conn()
        try:
            tables = [
                "conversation_turns", "conversations",
                "bill_items", "bills",
                "order_items", "orders",
                "reservations",
                "inventory",
                "fridge_ingredients",
                "restaurant_tables",
            ]
            for t in tables:
                conn.execute(f"DROP TABLE IF EXISTS {t}")
            conn.commit()
            for stmt in SCHEMA_SQL.split(";"):
                s = stmt.strip()
                if s:
                    conn.execute(s)
            _seed_data(conn)
        finally:
            conn.close()
