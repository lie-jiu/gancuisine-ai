"""Seed demo data into the restaurant system for testing and demonstration."""

from datetime import datetime, timedelta

from app.db.memory import db


def seed():
    """Add some sample reservations and orders for demo purposes."""
    # Create a reservation for tonight
    tonight = datetime.now().replace(hour=18, minute=30, second=0, microsecond=0)
    if tonight < datetime.now():
        tonight += timedelta(days=1)

    # Create some reservations
    res1 = db.create_reservation(
        customer="张三",
        phone="13800138001",
        party_size=4,
        time=tonight,
        table_id=3,
    )
    print(f"✅ Created reservation: {res1.id} (张三, 4人, {tonight.strftime('%H:%M')})")

    res2 = db.create_reservation(
        customer="李四",
        phone="13900139002",
        party_size=2,
        time=tonight + timedelta(hours=1),
        table_id=1,
        special_requests="靠窗位置，结婚纪念日",
    )
    print(f"✅ Created reservation: {res2.id} (李四, 2人, 窗边, 纪念日)")

    # Create an order
    order = db.create_order(table_id=3, customer_name="张三")
    from app.models.schemas import OrderItem
    order.items = [
        OrderItem(menu_item_id=3, quantity=1, menu_item_name="春卷"),
        OrderItem(menu_item_id=1, quantity=1, menu_item_name="宫保鸡丁"),
        OrderItem(menu_item_id=5, quantity=2, menu_item_name="蛋炒饭"),
    ]
    order.total = 32.0 + 68.0 + 38.0 * 2
    db.orders[order.id] = order
    print(f"✅ Created order: {order.id} (table 3, ¥{order.total:.0f})")

    # Occupy table 3
    db.tables[3].status = "occupied"
    print("✅ Table 3 marked as occupied")

    print("\n🎉 Seed data loaded successfully!")


if __name__ == "__main__":
    seed()
