import os
from decimal import Decimal
from datetime import date, timedelta
from dotenv import load_dotenv

from app.database import engine, Base, SessionLocal
from app.models import (
    Supplier, Customer, Item, Sale, SaleItem, User,
    PendingOrder, PendingOrderItem, OrderPayment, OrderStatusHistory,
    ItemCategory, ItemDescription, ShopSetting, StockMovement,
    Purchase, PurchaseItem, CustomerLedger, SupplierLedger
)
from app.services import next_code, apply_stock_change, money, ensure_walk_in_customer, reserve_item_stock, CATEGORIES, ITEM_TYPES

load_dotenv()
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    print("Seeding Ahmad Shop (Facewash, Body Wash, Shampoo, Hair Oil, Sunscreen, Hand Creams & Sunblocks)...")

    # 1. Shop Setting
    shop = db.query(ShopSetting).first()
    if not shop:
        shop = ShopSetting(
            shop_name="Ahmad Shop",
            shop_tagline="Facewash, Body Wash, Hair Care & Sun Protection Essentials",
            phone="+92 321 4143512",
            email="contact@ahmadshop.com",
            address="Shop 14, Luxury Galleria, Main Boulevard, Lahore",
            currency_symbol="Rs.",
            receipt_footer="Thank you for choosing Ahmad Shop! Return or exchange valid within 7 days with receipt in sealed condition."
        )
        db.add(shop)
        db.flush()
    else:
        shop.shop_name = "Ahmad Shop"
        shop.shop_tagline = "Facewash, Body Wash, Hair Care & Sun Protection Essentials"
        shop.email = "contact@ahmadshop.com"
        shop.receipt_footer = "Thank you for choosing Ahmad Shop! Return or exchange valid within 7 days with receipt in sealed condition."
        db.flush()

    # 2. Categories
    for cat_name in CATEGORIES:
        if not db.query(ItemCategory).filter(ItemCategory.name == cat_name).first():
            db.add(ItemCategory(name=cat_name))
    db.flush()

    # 3. Formulations / Types
    for fmt in ITEM_TYPES:
        if not db.query(ItemDescription).filter(ItemDescription.name == fmt).first():
            db.add(ItemDescription(name=fmt))
    db.flush()

    # 4. Walk-in customer
    ensure_walk_in_customer(db)

    # 5. Suppliers
    suppliers_data = [
        ("Unilever Personal Care Dist", "Tariq Amin", "0300-5551234", "Plot 12, Industrial Boulevard, Karachi", 25000),
        ("L'Oreal Consumer Products Division", "Sarah Khan", "0321-7774321", "Phase 8 Commercial, DHA Lahore", 15000),
        ("Johnson & Johnson Consumer Health", "Farhan Malik", "0333-8889900", "Blue Area, Islamabad", 0),
        ("Beiersdorf (Nivea / Eucerin) Supply Center", "Ayesha Siddiqui", "0345-1239876", "Clifton Block 5, Karachi", 0),
        ("Saeed Ghani Herbal Care Distribution", "M. Bilal", "0312-6655443", "Anarkali Commercial Zone, Lahore", 8000),
    ]
    created_suppliers = {}
    for name, cp, phone, addr, bal in suppliers_data:
        s = db.query(Supplier).filter(Supplier.name == name).first()
        if not s:
            s = Supplier(
                supplier_code=next_code(db, Supplier, "supplier_code", "SUPP"),
                name=name, contact_person=cp, phone=phone, address=addr,
                opening_balance=bal, current_balance=bal, status="Active"
            )
            db.add(s)
            db.flush()
        created_suppliers[name] = s

    # 6. Customers
    customers_data = [
        ("Al-Noor Aesthetics & Skin Clinic", "0301-4445566", "Gulberg III, Lahore", "Dermatology Clinic Account", 12500),
        ("Glow Wellness Studio & Day Spa", "0322-8881122", "DHA Phase 5, Karachi", "Spa & Wellness Client", 0),
        ("Royal Care Pharmacy & Beauty", "0334-9993344", "F-7 Markaz, Islamabad", "Retail Pharmacy Partner", 18500),
        ("Serene Derma Lounge", "0312-3334455", "Mall of Lahore", "Aesthetic Center", 0),
    ]
    created_customers = {}
    for name, phone, addr, proj, bal in customers_data:
        c = db.query(Customer).filter(Customer.name == name).first()
        if not c:
            c = Customer(
                customer_code=next_code(db, Customer, "customer_code", "CUST"),
                name=name, phone=phone, address=addr, vehicle_info=proj,
                opening_balance=bal, current_balance=bal, status="Active", is_walk_in=False
            )
            db.add(c)
            db.flush()
        created_customers[name] = c

    today = date.today()

    # 7. Comprehensive Catalog: facewash, body wash, shampoo, hair oil, sun screen, hand creams, sun blocks
    catalog = [
        # --- FACE WASH ---
        {
            "brand": "CeraVe", "name": "Foaming Facial Cleanser for Normal to Oily Skin", "barcode": "CRV-FC236",
            "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Ceramides & Niacinamide",
            "size_volume": "236ml", "skin_type": "Normal to Oily / Acne-Prone", "purchase_price": 3800.00,
            "sale_price": 5200.00, "discount": 0.00, "stock": 45, "reorder": 8, "unit": "Pump Bottle",
            "batch_no": "CRV8921", "expiry_date": today + timedelta(days=620)
        },
        {
            "brand": "CeraVe", "name": "Hydrating Facial Cleanser for Normal to Dry Skin", "barcode": "CRV-HC236",
            "category": "Face Wash & Cleansers", "description": "Cream & Lotion", "shade": "Hyaluronic Acid & Ceramides",
            "size_volume": "236ml", "skin_type": "Normal to Dry / Sensitive", "purchase_price": 3800.00,
            "sale_price": 5200.00, "discount": 0.00, "stock": 38, "reorder": 6, "unit": "Pump Bottle",
            "batch_no": "CRV8922", "expiry_date": today + timedelta(days=580)
        },
        {
            "brand": "Neutrogena", "name": "Oil-Free Acne Wash Pink Grapefruit Facial Cleanser", "barcode": "NTG-ACW175",
            "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "2% Salicylic Acid MicroClear",
            "size_volume": "175ml", "skin_type": "Oily & Acne-Prone", "purchase_price": 2400.00,
            "sale_price": 3400.00, "discount": 100.00, "stock": 30, "reorder": 5, "unit": "Pump Bottle",
            "batch_no": "NTG5501", "expiry_date": today + timedelta(days=500)
        },
        {
            "brand": "Cetaphil", "name": "Gentle Skin Cleanser Hydrating Formula", "barcode": "CTP-GSC250",
            "category": "Face Wash & Cleansers", "description": "Liquid & Wash", "shade": "Soap-Free Gentle",
            "size_volume": "250ml", "skin_type": "Dry to Normal / Sensitive", "purchase_price": 2900.00,
            "sale_price": 3950.00, "discount": 0.00, "stock": 25, "reorder": 5, "unit": "Bottle",
            "batch_no": "CTP3310", "expiry_date": today + timedelta(days=700)
        },
        {
            "brand": "Simple", "name": "Kind to Skin Refreshing Facial Wash 100% Soap Free", "barcode": "SMP-RFW150",
            "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Pro-Vitamin B5 & Vitamin E",
            "size_volume": "150ml", "skin_type": "All Skin Types / Sensitive", "purchase_price": 1400.00,
            "sale_price": 1950.00, "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Tube",
            "batch_no": "SMP1029", "expiry_date": today + timedelta(days=450)
        },

        # --- BODY WASH ---
        {
            "brand": "Dove", "name": "Deep Moisture Nourishing Body Wash", "barcode": "DVE-DMB450",
            "category": "Body Wash & Shower Gels", "description": "Cream & Lotion", "shade": "MicroMoisture Serum",
            "size_volume": "450ml", "skin_type": "Dry Skin", "purchase_price": 1800.00,
            "sale_price": 2500.00, "discount": 50.00, "stock": 40, "reorder": 8, "unit": "Pump Bottle",
            "batch_no": "DV402", "expiry_date": today + timedelta(days=600)
        },
        {
            "brand": "The Body Shop", "name": "British Rose Shower Gel Petal Soft", "barcode": "TBS-BRS250",
            "category": "Body Wash & Shower Gels", "description": "Gel & Foaming Gel", "shade": "English Rose Petals",
            "size_volume": "250ml", "skin_type": "All Skin Types", "purchase_price": 2800.00,
            "sale_price": 3900.00, "discount": 0.00, "stock": 20, "reorder": 4, "unit": "Bottle",
            "batch_no": "TBS771", "expiry_date": today + timedelta(days=720)
        },
        {
            "brand": "Nivea", "name": "Creme Soft Shower Gel with Almond Oil", "barcode": "NIV-CSS250",
            "category": "Body Wash & Shower Gels", "description": "Liquid & Wash", "shade": "Natural Almond Oil",
            "size_volume": "250ml", "skin_type": "Normal to Dry Skin", "purchase_price": 1250.00,
            "sale_price": 1750.00, "discount": 0.00, "stock": 35, "reorder": 6, "unit": "Bottle",
            "batch_no": "NV9102", "expiry_date": today + timedelta(days=650)
        },

        # --- SHAMPOO ---
        {
            "brand": "OGX", "name": "Renewing + Argan Oil of Morocco Shampoo", "barcode": "OGX-AOM385",
            "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Sulfate-Free Moroccan Argan",
            "size_volume": "385ml", "skin_type": "Dry & Damaged Hair", "purchase_price": 2700.00,
            "sale_price": 3750.00, "discount": 0.00, "stock": 28, "reorder": 5, "unit": "Bottle",
            "batch_no": "OGX441", "expiry_date": today + timedelta(days=750)
        },
        {
            "brand": "L'Oreal Paris", "name": "Total Repair 5 Restoring Shampoo", "barcode": "LOR-TR5360",
            "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Ceramide-R Protein Repair",
            "size_volume": "360ml", "skin_type": "Damaged Hair", "purchase_price": 1350.00,
            "sale_price": 1900.00, "discount": 0.00, "stock": 42, "reorder": 8, "unit": "Bottle",
            "batch_no": "LOR661", "expiry_date": today + timedelta(days=680)
        },
        {
            "brand": "Tresemme", "name": "Keratin Smooth Frizz Control Shampoo", "barcode": "TRS-KRS400",
            "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Keratin & Marula Oil",
            "size_volume": "400ml", "skin_type": "Frizzy & Unruly Hair", "purchase_price": 1600.00,
            "sale_price": 2250.00, "discount": 0.00, "stock": 36, "reorder": 6, "unit": "Bottle",
            "batch_no": "TRS821", "expiry_date": today + timedelta(days=580)
        },
        {
            "brand": "Head & Shoulders", "name": "Cool Menthol Anti-Dandruff Shampoo", "barcode": "HNS-CM360",
            "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Menthol Cooling Formula",
            "size_volume": "360ml", "skin_type": "Dandruff & Itchy Scalp", "purchase_price": 1400.00,
            "sale_price": 1950.00, "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Bottle",
            "batch_no": "HNS310", "expiry_date": today + timedelta(days=720)
        },

        # --- HAIR OIL ---
        {
            "brand": "Dabur", "name": "Vatika Enriched Coconut Hair Oil with Henna & Amla", "barcode": "DAB-VHK200",
            "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Herbal Coconut Nourishment",
            "size_volume": "200ml", "skin_type": "Hair Fall & Weak Roots", "purchase_price": 950.00,
            "sale_price": 1400.00, "discount": 0.00, "stock": 60, "reorder": 12, "unit": "Bottle",
            "batch_no": "DAB901", "expiry_date": today + timedelta(days=800)
        },
        {
            "brand": "L'Oreal Paris", "name": "Elvive Extraordinary Oil Multi-Use Hair Serum Treatment", "barcode": "LOR-EXO100",
            "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "6 Precious Micro-Flower Oils",
            "size_volume": "100ml", "skin_type": "Dry & Dull Hair", "purchase_price": 2600.00,
            "sale_price": 3650.00, "discount": 150.00, "stock": 24, "reorder": 5, "unit": "Pump Bottle",
            "batch_no": "LOR882", "expiry_date": today + timedelta(days=640)
        },
        {
            "brand": "Parachute", "name": "Advansed Aloe Vera Enriched Coconut Hair Oil", "barcode": "PAR-AVO150",
            "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Aloe Vera + Pure Coconut",
            "size_volume": "150ml", "skin_type": "All Hair Types", "purchase_price": 750.00,
            "sale_price": 1100.00, "discount": 0.00, "stock": 55, "reorder": 10, "unit": "Bottle",
            "batch_no": "PAR210", "expiry_date": today + timedelta(days=700)
        },
        {
            "brand": "Saeed Ghani", "name": "Mughziat Herbal Hair Oil Traditional Growth Blend", "barcode": "SGH-MGH120",
            "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Traditional Mughziat Extract",
            "size_volume": "120ml", "skin_type": "Hair Thinning & Scalp Health", "purchase_price": 850.00,
            "sale_price": 1250.00, "discount": 0.00, "stock": 48, "reorder": 8, "unit": "Bottle",
            "batch_no": "SGH119", "expiry_date": today + timedelta(days=650)
        },

        # --- SUN SCREEN & SUN BLOCKS ---
        {
            "brand": "La Roche-Posay", "name": "Anthelios UVMune 400 Invisible Fluid SPF 50+", "barcode": "LRP-UV50",
            "category": "Sunscreens & Sunblocks", "description": "Sunscreen Spray / Fluid", "shade": "SPF 50+ Broad Spectrum",
            "size_volume": "50ml", "skin_type": "Sensitive & All Skin Types", "purchase_price": 6200.00,
            "sale_price": 8400.00, "discount": 0.00, "stock": 32, "reorder": 6, "unit": "Bottle",
            "batch_no": "LRP401", "expiry_date": today + timedelta(days=580)
        },
        {
            "brand": "Neutrogena", "name": "Ultra Sheer Dry-Touch Sunblock SPF 50+", "barcode": "NTG-USD50",
            "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 50+ Helioplex Matte",
            "size_volume": "88ml", "skin_type": "Normal to Oily Skin", "purchase_price": 3100.00,
            "sale_price": 4350.00, "discount": 100.00, "stock": 35, "reorder": 8, "unit": "Tube",
            "batch_no": "NTG992", "expiry_date": today + timedelta(days=500)
        },
        {
            "brand": "Biore", "name": "UV Aqua Rich Watery Essence SPF 50+ PA++++", "barcode": "BIO-AQU50",
            "category": "Sunscreens & Sunblocks", "description": "Gel & Foaming Gel", "shade": "SPF 50+ PA++++ Water Gel",
            "size_volume": "50g", "skin_type": "All Skin Types / No White Cast", "purchase_price": 3400.00,
            "sale_price": 4750.00, "discount": 0.00, "stock": 28, "reorder": 6, "unit": "Tube",
            "batch_no": "BIO550", "expiry_date": today + timedelta(days=560)
        },
        {
            "brand": "CeraVe", "name": "Hydrating Mineral Sunscreen Sheer Tint SPF 30", "barcode": "CRV-SUN30",
            "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 30 Mineral Tint",
            "size_volume": "50ml", "skin_type": "Sensitive & Dry Skin", "purchase_price": 5400.00,
            "sale_price": 7200.00, "discount": 0.00, "stock": 18, "reorder": 4, "unit": "Tube",
            "batch_no": "CRV771", "expiry_date": today + timedelta(days=520)
        },
        {
            "brand": "Eveline", "name": "Sun Protection Face Cream Sunblock SPF 50 High Protection", "barcode": "EVL-SPF50",
            "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 50 UVA/UVB Shield",
            "size_volume": "50ml", "skin_type": "All Skin Types / Anti-Shine", "purchase_price": 2100.00,
            "sale_price": 2950.00, "discount": 0.00, "stock": 4, "reorder": 8, "unit": "Tube",
            "batch_no": "EVL229", "expiry_date": today + timedelta(days=360)
        }, # Low stock test item

        # --- HAND CREAMS ---
        {
            "brand": "Neutrogena", "name": "Norwegian Formula Concentrated Hand Cream Fragrance-Free", "barcode": "NTG-NWH50",
            "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Glycerin Rich Intensive Relief",
            "size_volume": "50ml", "skin_type": "Dry & Chapped Hands", "purchase_price": 1600.00,
            "sale_price": 2300.00, "discount": 0.00, "stock": 35, "reorder": 6, "unit": "Tube",
            "batch_no": "NTG810", "expiry_date": today + timedelta(days=640)
        },
        {
            "brand": "L'Occitane", "name": "Shea Butter Intensive Hand Balm Cream 20%", "barcode": "LOC-SHB75",
            "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "20% Organic Shea Butter",
            "size_volume": "75ml", "skin_type": "Very Dry & Damaged Hands", "purchase_price": 6800.00,
            "sale_price": 9200.00, "discount": 200.00, "stock": 15, "reorder": 3, "unit": "Tube",
            "batch_no": "LOC991", "expiry_date": today + timedelta(days=700)
        },
        {
            "brand": "Nivea", "name": "Smooth Hands Nourishing Hand Cream Shea Butter", "barcode": "NIV-SMH100",
            "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "24H Protective Shea Butter",
            "size_volume": "100ml", "skin_type": "Normal to Dry Hands", "purchase_price": 1100.00,
            "sale_price": 1600.00, "discount": 0.00, "stock": 40, "reorder": 8, "unit": "Tube",
            "batch_no": "NIV601", "expiry_date": today + timedelta(days=620)
        },
        {
            "brand": "Vaseline", "name": "Intensive Care Healthy Hands & Stronger Nails Cream", "barcode": "VAS-HHN75",
            "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Keratin & Vaseline Jelly",
            "size_volume": "75ml", "skin_type": "Hands, Cuticles & Nails", "purchase_price": 950.00,
            "sale_price": 1400.00, "discount": 0.00, "stock": 45, "reorder": 8, "unit": "Tube",
            "batch_no": "VAS330", "expiry_date": today + timedelta(days=580)
        },
    ]

    for item_data in catalog:
        exists = db.query(Item).filter(Item.barcode == item_data["barcode"]).first()
        if not exists:
            new_item = Item(
                item_code=next_code(db, Item, "item_code", "SKU"),
                brand=item_data["brand"],
                name=item_data["name"],
                barcode=item_data["barcode"],
                category=item_data["category"],
                description=item_data["description"],
                shade=item_data["shade"],
                size_volume=item_data["size_volume"],
                skin_type=item_data["skin_type"],
                purchase_price=Decimal(str(item_data["purchase_price"])),
                sale_price=Decimal(str(item_data["sale_price"])),
                discount=Decimal(str(item_data["discount"])),
                current_stock=item_data["stock"],
                reserved_stock=0,
                reorder_level=item_data["reorder"],
                unit=item_data["unit"],
                batch_no=item_data["batch_no"],
                expiry_date=item_data["expiry_date"],
                status="Active"
            )
            db.add(new_item)
            db.flush()

            # Record initial inward movement
            db.add(StockMovement(
                item_id=new_item.id,
                movement_type="purchase",
                quantity_change=item_data["stock"],
                quantity_after=item_data["stock"],
                note="Initial inventory stocking - Personal Care Catalog"
            ))

    db.commit()
    print("Catalog seed completed successfully!")
    print(f"Total categories: {len(CATEGORIES)}")
    print(f"Total catalog products seeded: {len(catalog)}")

except Exception as e:
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
