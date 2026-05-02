"""In-memory state store — serves as the restaurant's "database".

江西特色：没有菜单，全部食材摆冰柜，客人看着冰柜点菜。

数据存储已迁移至 SQLite（data/restaurant.db），此模块保留为兼容层。
"""

from __future__ import annotations

from app.db.database import SqliteRestaurantDB


# Singleton — now SQLite-backed, persistent across restarts
db = SqliteRestaurantDB()
