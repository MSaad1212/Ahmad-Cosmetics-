"""
Database Migration for Ahmad Cosmetics:
- Adds shade, size_volume, skin_type, discount, reserved_stock, batch_no, expiry_date to items table
- Creates shop_settings, pending_orders, pending_order_items, order_payments, order_status_history tables
- Safe and idempotent
"""
from sqlalchemy import text, inspect
from app.database import engine, Base
from app.models import ShopSetting, PendingOrder, PendingOrderItem, OrderPayment, OrderStatusHistory

def run_migration():
    print("Running database migration...")
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("items")]

        new_cols = [
            ("shade", "VARCHAR(100) NULL"),
            ("size_volume", "VARCHAR(50) NULL"),
            ("skin_type", "VARCHAR(100) NULL"),
            ("discount", "DECIMAL(12, 2) NOT NULL DEFAULT 0.00"),
            ("reserved_stock", "INT NOT NULL DEFAULT 0"),
            ("batch_no", "VARCHAR(50) NULL"),
            ("expiry_date", "DATE NULL"),
        ]

        for col_name, col_type in new_cols:
            if col_name not in columns:
                print(f"Adding column '{col_name}' to items table...")
                conn.execute(text(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            else:
                print(f"Column '{col_name}' already exists in items.")

    # Create new tables if not exist
    Base.metadata.create_all(bind=engine)
    print("All tables verified and created successfully.")

if __name__ == "__main__":
    run_migration()
