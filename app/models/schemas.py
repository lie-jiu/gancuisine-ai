"""Pydantic data models / schemas for all entities.

Adapted for 江西 style: no traditional menu, ingredients displayed in refrigerated cabinets (冰柜).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────

class TableStatus(str, Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    served = "served"
    cancelled = "cancelled"


class ReservationStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class AgentType(str, Enum):
    supervisor = "supervisor"
    receptionist = "receptionist"
    waiter = "waiter"
    chef = "chef"
    sommelier = "sommelier"


class IngredientCategory(str, Enum):
    """类别：冰柜食材分类"""
    vegetable = "vegetable"       # 蔬菜
    meat = "meat"                 # 肉类
    poultry = "poultry"           # 禽类
    seafood = "seafood"           # 水产/海鲜
    tofu_egg = "tofu_egg"        # 豆制品/蛋类
    preserved = "preserved"       # 腊味/腌制品
    seasoning = "seasoning"       # 调料/配料
    other = "other"               # 其他


class CookingMethod(str, Enum):
    """赣菜烹饪方式"""
    stir_fry = "小炒"              # 江西小炒
    steam = "清蒸"                 # 清蒸
    braise = "红烧"                # 红烧
    stew = "炖"                    # 瓦罐煨汤
    steam_with_rice_flour = "粉蒸" # 粉蒸肉
    cold_mix = "凉拌"              # 凉拌
    deep_fry = "油炸"              # 油炸
    boil = "煮"                    # 煮
    smoke = "烟熏"                 # 烟熏
    clay_pot = "煲"                # 煲


# ── Tables ─────────────────────────────────────────────

class Table(BaseModel):
    id: int
    capacity: int
    status: TableStatus = TableStatus.available
    location: str = ""  # e.g. "窗边", "包间", "大厅"


# ── 冰柜食材 (replaces traditional MenuItem) ───────────

class FridgeIngredient(BaseModel):
    """冰柜里展示的食材——江西特色：没有菜单，客人看冰柜点菜"""
    id: int
    name: str
    name_zh: str
    category: IngredientCategory = IngredientCategory.other
    price_per_500g: float = 0.0        # 每斤价格（江西习惯按斤算）
    available_kg: float = 0.0          # 当前库存公斤数
    description: str = ""              # 产地/品质描述
    season: str = "全年"               # 季节
    suggested_methods: list[CookingMethod] = Field(default_factory=list)  # 适合的烹饪方式
    image_url: str = ""                # 冰柜实拍图


class FridgeDisplay(BaseModel):
    """冰柜展示区——按类别陈列"""
    category: IngredientCategory
    label: str
    ingredients: list[FridgeIngredient]


# ── 烹饪建议 ───────────────────────────────────────────

class DishSuggestion(BaseModel):
    """基于冰柜食材的菜品建议"""
    name: str                          # 菜名
    name_zh: str                       # 中文菜名
    main_ingredients: list[str]        # 主料
    method: CookingMethod              # 烹饪方式
    estimated_price: float             # 估计价格
    prep_time_minutes: int             # 预计制作时间
    description: str = ""              # 做法简介
    is_signature: bool = False         # 是否招牌做法

    @property
    def display(self) -> str:
        methods_display = " + ".join(m.value for m in [self.method])
        return (
            f"🍳 {self.name_zh}（{self.name}）\n"
            f"   主料: {', '.join(self.main_ingredients)}\n"
            f"   做法: {methods_display}\n"
            f"   价格: ¥{self.estimated_price:.0f}\n"
            f"   用时: {self.prep_time_minutes}分钟\n"
            f"   {'🔥 招牌推荐！' if self.is_signature else ''}"
        )


# ── Orders ─────────────────────────────────────────────

class OrderItem(BaseModel):
    """点菜单项——取代menu_item_id，直接记录菜名和食材"""
    dish_name: str = ""                # 菜品名称
    ingredients_used: list[str] = Field(default_factory=list)  # 使用的食材
    cooking_method: str = "小炒"       # 烹饪方式
    quantity: int = 1
    unit_price: float = 0.0
    notes: str = ""


class Order(BaseModel):
    id: str
    table_id: int
    customer_name: str = ""
    items: list[OrderItem] = Field(default_factory=list)
    status: OrderStatus = OrderStatus.pending
    created_at: datetime = Field(default_factory=datetime.now)
    total: float = 0.0


# ── Reservations ───────────────────────────────────────

class Reservation(BaseModel):
    id: str
    customer_name: str
    phone: str = ""
    party_size: int
    time: datetime
    table_id: Optional[int] = None
    status: ReservationStatus = ReservationStatus.confirmed
    special_requests: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# ── Inventory (厨房备货) ────────────────────────────────

class Ingredient(BaseModel):
    name: str
    quantity_kg: float = 0.0
    unit: str = "斤"
    min_threshold: float = 2.0


# ── Bills ──────────────────────────────────────────────

class BillItem(BaseModel):
    description: str
    quantity: int
    unit_price: float


class Bill(BaseModel):
    table_id: int
    items: list[BillItem] = Field(default_factory=list)
    subtotal: float = 0.0
    service_charge: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    paid: bool = False


# ── Vision (视觉识别结果) ───────────────────────────────

class IdentifiedIngredient(BaseModel):
    """从冰柜照片中识别出的食材"""
    name: str
    name_zh: str
    confidence: float = 0.0           # 识别置信度
    category: IngredientCategory = IngredientCategory.other
    estimated_weight_kg: float = 0.5  # 目测大概有多少
    matched_fridge_id: Optional[int] = None  # 匹配到的冰柜食材ID


class FridgeScanResult(BaseModel):
    """冰柜扫描结果"""
    identified: list[IdentifiedIngredient] = Field(default_factory=list)
    suggestions: list[DishSuggestion] = Field(default_factory=list)
    raw_analysis: str = ""


# ── Chat / Conversation ────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    customer_name: str = ""


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent: AgentType = AgentType.supervisor


class ConversationTurn(BaseModel):
    role: str  # "customer" | "agent"
    message: str
    agent: AgentType = AgentType.supervisor
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    session_id: str
    customer_name: str = ""
    turns: list[ConversationTurn] = Field(default_factory=list)
    active_order_id: Optional[str] = None
    active_reservation_id: Optional[str] = None
