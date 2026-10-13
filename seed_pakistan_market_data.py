"""Pakistan Market Data Seeder for Ahmad Shop.
Populates realistic Pakistani market data for:
- Face Wash & Cleansers (Pond's, Garnier, Himalaya, CeraVe, Simple, Clean & Clear, Saeed Ghani)
- Body Wash & Shower Gels (Lifebuoy, Dettol, Dove, Lux, Palmolive, Nivea)
- Shampoos (Sunsilk, Head & Shoulders, Pantene, Clear, L'Oreal, Tresemme, Bio Amla)
- Hair Oils (Bio Amla, Dabur Amla, Dabur Vatika, Parachute, Saeed Ghani, Roghan Badam)
- Sunscreens & Sunblocks (U-Veil Forte, Solaris Ultra, Vince, Rivaj UK, Jenpharm Spectra, Neutrogena, La Roche-Posay)
- Hand Creams (Nivea Soft, Vaseline, Saeed Ghani, Golden Pearl, Neutrogena)
Together with Pakistani distributors, salons/retail accounts, purchases, and sales.
"""
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
from app.services import (
    next_code, apply_stock_change, money, ensure_walk_in_customer,
    add_customer_ledger, add_supplier_ledger, CATEGORIES, ITEM_TYPES
)

load_dotenv()
Base.metadata.create_all(bind=engine)

def seed_pakistan_data():
    db = SessionLocal()
    try:
        print("Starting Pakistan Market Data Seeding for Ahmad Shop...")

        # 1. Shop Setting
        shop = db.query(ShopSetting).first()
        if not shop:
            shop = ShopSetting(
                shop_name="Ahmad Shop",
                shop_tagline="Facewash, Body Wash, Hair Care & Sun Protection Essentials",
                phone="0321-4143512",
                email="contact@ahmadshop.com",
                address="Shop #12, Commercial Market, Main Boulevard, Lahore",
                currency_symbol="Rs.",
                receipt_footer="Thank you for shopping at Ahmad Shop! Return/exchange valid within 7 days in sealed condition with original receipt."
            )
            db.add(shop)
            db.flush()
        else:
            shop.shop_name = "Ahmad Shop"
            shop.shop_tagline = "Facewash, Body Wash, Hair Care & Sun Protection Essentials"
            shop.address = "Shop #12, Commercial Market, Main Boulevard, Lahore"
            shop.phone = "0321-4143512"
            shop.email = "contact@ahmadshop.com"
            shop.currency_symbol = "Rs."
            shop.receipt_footer = "Thank you for shopping at Ahmad Shop! Return/exchange valid within 7 days in sealed condition with original receipt."
            db.flush()

        # 2. Categories
        for cat in CATEGORIES:
            if not db.query(ItemCategory).filter(ItemCategory.name == cat).first():
                db.add(ItemCategory(name=cat))
        db.flush()

        # 3. Item Formulations / Types
        for t in ITEM_TYPES:
            if not db.query(ItemDescription).filter(ItemDescription.name == t).first():
                db.add(ItemDescription(name=t))
        db.flush()

        # 4. Walk-in Customer
        walk_in = ensure_walk_in_customer(db)

        # 5. Pakistani Distributors / Suppliers
        pak_suppliers = [
            ("Unilever Pakistan Distribution Network", "Tariq Mahmood", "0300-5551234", "Plot 14, Quaid-e-Azam Industrial Estate, Kot Lakhpat, Lahore", 35000),
            ("Muller & Phipps Pakistan (Pvt) Ltd", "Farhan Siddiqui", "0321-4455667", "P.E.C.H.S Block 6, Karachi", 42000),
            ("L'Oreal & Garnier Consumer Supply Hub", "Kamran Malik", "0333-8877665", "Phase 5 Commercial Area, DHA Lahore", 28000),
            ("Bio Amla & Forvil Cosmetics Ltd", "Sheikh M. Aslam", "0300-9421122", "12-Km Multan Road Industrial Estate, Lahore", 12000),
            ("Saeed Ghani Herbal & Natural Products", "Haji Bilal Ghani", "0312-4433221", "Shop 45, Bhati Gate / Circular Road, Lahore", 8500),
            ("Derma Tech & Skin Pharma Distributors", "Dr. Usman Qureshi", "0345-6677889", "Blue Area, Jinnah Avenue, Islamabad", 24000),
            ("Beiersdorf Pakistan (Nivea Supply)", "Zahid Rasheed", "0322-7711223", "Main Korangi Industrial Road, Karachi", 16000),
        ]

        supplier_map = {}
        for name, cp, phone, addr, bal in pak_suppliers:
            s = db.query(Supplier).filter(Supplier.name == name).first()
            if not s:
                s = Supplier(
                    supplier_code=next_code(db, Supplier, "supplier_code", "SUPP"),
                    name=name, contact_person=cp, phone=phone, address=addr,
                    opening_balance=0, current_balance=0, status="Active"
                )
                db.add(s)
                db.flush()
                # Opening ledger
                if bal > 0:
                    add_supplier_ledger(
                        db, s, date.today() - timedelta(days=30),
                        "Opening Account Balance Payable", debit=Decimal(str(bal)), credit=Decimal("0"),
                        reference_type="opening"
                    )
            supplier_map[name] = s

        # 6. Pakistani Market Customers
        pak_customers = [
            ("Dr. Farhana Skin & Aesthetics Clinic", "0300-4123890", "DHA Phase 6, Lahore", "Dermatology Aesthetics Account", 18500),
            ("Kashees Beauty Salon & Bridal Studio", "0321-8899120", "Gulshan-e-Iqbal Block 4, Karachi", "VIP Salon Wholesale Account", 26000),
            ("Al-Madina Pharmacy & General Store", "0333-5566778", "Bank Road, Saddar, Rawalpindi", "Retail Pharmacy Partner", 14500),
            ("Aura Wellness & Day Spa", "0345-7788990", "F-8 Markaz, Islamabad", "Corporate Spa Account", 9500),
            ("Mrs. Tahira Babar (VIP Customer)", "0312-9988776", "House 42, Model Town C-Block, Lahore", "Loyal Family Account", 0),
            ("Bismah Khan (Regular Customer)", "0301-3344556", "Apartment 12-B, Gulberg Heights, Lahore", "Monthly Personal Care Subscriber", 0),
        ]

        customer_map = {}
        for name, phone, addr, note, bal in pak_customers:
            c = db.query(Customer).filter(Customer.name == name).first()
            if not c:
                c = Customer(
                    customer_code=next_code(db, Customer, "customer_code", "CUST"),
                    name=name, phone=phone, address=addr, vehicle_info=note,
                    opening_balance=0, current_balance=0, status="Active", is_walk_in=False
                )
                db.add(c)
                db.flush()
                if bal > 0:
                    add_customer_ledger(
                        db, c, date.today() - timedelta(days=20),
                        "Opening Account Balance Receivable", debit=Decimal(str(bal)), credit=Decimal("0"),
                        reference_type="opening"
                    )
            customer_map[name] = c

        today = date.today()

        # 7. Comprehensive Catalog - Pakistan Market
        products = [
            # ======================== 1. FACE WASH ========================
            {
                "brand": "Pond's", "name": "Bright Beauty Spot-less Glow Face Wash", "barcode": "896101412001",
                "category": "Face Wash & Cleansers", "description": "Foam Cleanser", "shade": "Vitamin B3+ Formula",
                "size_volume": "100g", "skin_type": "All Skin Types", "purchase_price": 370.00, "sale_price": 480.00,
                "discount": 0.00, "stock": 48, "reorder": 10, "unit": "Tube", "batch_no": "PND-PK2401",
                "expiry_date": today + timedelta(days=600), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Pond's", "name": "Pure Detox Mineral Clay Facial Foam Face Wash", "barcode": "896101412002",
                "category": "Face Wash & Cleansers", "description": "Foam Cleanser", "shade": "Activated Charcoal Detox",
                "size_volume": "100g", "skin_type": "Oily & Pollution Prone", "purchase_price": 400.00, "sale_price": 520.00,
                "discount": 0.00, "stock": 36, "reorder": 8, "unit": "Tube", "batch_no": "PND-PK2402",
                "expiry_date": today + timedelta(days=580), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Garnier", "name": "SkinActive Fast Fairness Vitamin C Face Wash", "barcode": "896101412003",
                "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Pure Lemon & Vitamin C",
                "size_volume": "100ml", "skin_type": "All Skin Types / Dull Skin", "purchase_price": 510.00, "sale_price": 650.00,
                "discount": 20.00, "stock": 40, "reorder": 8, "unit": "Tube", "batch_no": "GAR-PK2403",
                "expiry_date": today + timedelta(days=700), "supp": "L'Oreal & Garnier Consumer Supply Hub"
            },
            {
                "brand": "Himalaya", "name": "Purifying Neem Face Wash Anti-Acne Formula", "barcode": "896101412004",
                "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Neem & Turmeric Herbal",
                "size_volume": "150ml", "skin_type": "Acne-Prone & Sensitive", "purchase_price": 580.00, "sale_price": 750.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Tube", "batch_no": "HIM-PK2404",
                "expiry_date": today + timedelta(days=640), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Clean & Clear", "name": "Foaming Face Wash Oil-Free", "barcode": "896101412005",
                "category": "Face Wash & Cleansers", "description": "Liquid & Wash", "shade": "Original Oil Control",
                "size_volume": "100ml", "skin_type": "Oily Skin", "purchase_price": 420.00, "sale_price": 550.00,
                "discount": 0.00, "stock": 35, "reorder": 8, "unit": "Bottle", "batch_no": "CNC-PK2405",
                "expiry_date": today + timedelta(days=550), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Saeed Ghani", "name": "Neem & Tea Tree Face Wash Herbal Purifying", "barcode": "896101412006",
                "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Natural Tea Tree Extract",
                "size_volume": "100ml", "skin_type": "Pimple & Blemish Prone", "purchase_price": 280.00, "sale_price": 380.00,
                "discount": 0.00, "stock": 60, "reorder": 12, "unit": "Tube", "batch_no": "SGH-PK2406",
                "expiry_date": today + timedelta(days=480), "supp": "Saeed Ghani Herbal & Natural Products"
            },
            {
                "brand": "CeraVe", "name": "Foaming Facial Cleanser for Normal to Oily Skin", "barcode": "896101412007",
                "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Ceramides & Niacinamide",
                "size_volume": "236ml", "skin_type": "Oily & Sensitive Skin", "purchase_price": 2950.00, "sale_price": 3850.00,
                "discount": 0.00, "stock": 18, "reorder": 4, "unit": "Pump Bottle", "batch_no": "CRV-IMP2407",
                "expiry_date": today + timedelta(days=720), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Simple", "name": "Kind to Skin Refreshing Facial Wash 100% Soap Free", "barcode": "896101412008",
                "category": "Face Wash & Cleansers", "description": "Gel & Foaming Gel", "shade": "Pro-Vitamin B5 Sensitive",
                "size_volume": "150ml", "skin_type": "Sensitive & All Skin Types", "purchase_price": 1280.00, "sale_price": 1650.00,
                "discount": 0.00, "stock": 25, "reorder": 5, "unit": "Tube", "batch_no": "SMP-IMP2408",
                "expiry_date": today + timedelta(days=590), "supp": "Unilever Pakistan Distribution Network"
            },

            # ======================== 2. BODY WASH ========================
            {
                "brand": "Lifebuoy", "name": "Total 10 Germ Protection Body Wash", "barcode": "896101412009",
                "category": "Body Wash & Shower Gels", "description": "Liquid & Wash", "shade": "Active Silver Formula",
                "size_volume": "500ml", "skin_type": "All Family Members", "purchase_price": 660.00, "sale_price": 850.00,
                "discount": 0.00, "stock": 42, "reorder": 10, "unit": "Pump Bottle", "batch_no": "LFB-PK2409",
                "expiry_date": today + timedelta(days=650), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Dettol", "name": "Cool Antibacterial Body Wash with Crispy Menthol", "barcode": "896101412010",
                "category": "Body Wash & Shower Gels", "description": "Liquid & Wash", "shade": "Menthol Cooling Refresh",
                "size_volume": "250ml", "skin_type": "All Skin Types", "purchase_price": 420.00, "sale_price": 550.00,
                "discount": 0.00, "stock": 38, "reorder": 8, "unit": "Bottle", "batch_no": "DTL-PK2410",
                "expiry_date": today + timedelta(days=600), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Dove", "name": "Deep Moisture Nourishing Body Wash", "barcode": "896101412011",
                "category": "Body Wash & Shower Gels", "description": "Cream & Lotion", "shade": "NutriumMoisture Serum",
                "size_volume": "500ml", "skin_type": "Dry & Sensitive Skin", "purchase_price": 1380.00, "sale_price": 1780.00,
                "discount": 50.00, "stock": 30, "reorder": 6, "unit": "Pump Bottle", "batch_no": "DVE-PK2411",
                "expiry_date": today + timedelta(days=700), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Nivea", "name": "Creme Care Shower Gel with Pro-Vitamin Care", "barcode": "896101412012",
                "category": "Body Wash & Shower Gels", "description": "Liquid & Wash", "shade": "Classic Nivea Scent",
                "size_volume": "250ml", "skin_type": "Normal to Dry Skin", "purchase_price": 680.00, "sale_price": 890.00,
                "discount": 0.00, "stock": 28, "reorder": 5, "unit": "Bottle", "batch_no": "NIV-PK2412",
                "expiry_date": today + timedelta(days=620), "supp": "Beiersdorf Pakistan (Nivea Supply)"
            },
            {
                "brand": "Lux", "name": "Magical Orchid Fragrance Body Wash 24H", "barcode": "896101412013",
                "category": "Body Wash & Shower Gels", "description": "Liquid & Wash", "shade": "Black Orchid & Juniper Oil",
                "size_volume": "250ml", "skin_type": "All Skin Types", "purchase_price": 370.00, "sale_price": 480.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Bottle", "batch_no": "LUX-PK2413",
                "expiry_date": today + timedelta(days=750), "supp": "Unilever Pakistan Distribution Network"
            },

            # ======================== 3. SHAMPOO ========================
            {
                "brand": "Sunsilk", "name": "Thick & Long Shampoo with Keratin Yoghurt", "barcode": "896101412014",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Keratin Yoghurt Complex",
                "size_volume": "370ml", "skin_type": "Thin & Fine Hair", "purchase_price": 500.00, "sale_price": 650.00,
                "discount": 0.00, "stock": 55, "reorder": 12, "unit": "Bottle", "batch_no": "SNK-PK2414",
                "expiry_date": today + timedelta(days=700), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Sunsilk", "name": "Co-Creations Stunning Black Shine Shampoo", "barcode": "896101412015",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Amla Pearl Complex",
                "size_volume": "370ml", "skin_type": "Dull & Normal Hair", "purchase_price": 500.00, "sale_price": 650.00,
                "discount": 0.00, "stock": 60, "reorder": 12, "unit": "Bottle", "batch_no": "SNK-PK2415",
                "expiry_date": today + timedelta(days=700), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Pantene", "name": "Pro-V Hair Fall Control Shampoo", "barcode": "896101412016",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Pro-V Keratin Nourishment",
                "size_volume": "360ml", "skin_type": "Hair Fall & Weak Roots", "purchase_price": 580.00, "sale_price": 750.00,
                "discount": 0.00, "stock": 45, "reorder": 10, "unit": "Bottle", "batch_no": "PNT-PK2416",
                "expiry_date": today + timedelta(days=680), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Head & Shoulders", "name": "Cool Menthol Anti-Dandruff Shampoo", "barcode": "896101412017",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Cooling Menthol Blast",
                "size_volume": "360ml", "skin_type": "Dandruff & Flaky Scalp", "purchase_price": 660.00, "sale_price": 850.00,
                "discount": 0.00, "stock": 52, "reorder": 10, "unit": "Bottle", "batch_no": "HNS-PK2417",
                "expiry_date": today + timedelta(days=750), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Bio Amla", "name": "Herbal Shampoo Traditional Formula", "barcode": "896101412018",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Natural Amla & Shikakai",
                "size_volume": "300ml", "skin_type": "All Hair Types / Herbal Care", "purchase_price": 290.00, "sale_price": 380.00,
                "discount": 0.00, "stock": 65, "reorder": 15, "unit": "Bottle", "batch_no": "BAM-PK2418",
                "expiry_date": today + timedelta(days=800), "supp": "Bio Amla & Forvil Cosmetics Ltd"
            },
            {
                "brand": "L'Oreal Paris", "name": "Total Repair 5 Restoring Shampoo with Ceramide", "barcode": "896101412019",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Ceramide-R Protein Repair",
                "size_volume": "360ml", "skin_type": "Damaged & Split Ends", "purchase_price": 1050.00, "sale_price": 1350.00,
                "discount": 50.00, "stock": 35, "reorder": 6, "unit": "Bottle", "batch_no": "LOR-PK2419",
                "expiry_date": today + timedelta(days=720), "supp": "L'Oreal & Garnier Consumer Supply Hub"
            },
            {
                "brand": "Tresemme", "name": "Keratin Smooth Frizz Control Shampoo", "barcode": "896101412020",
                "category": "Shampoos & Hair Cleansers", "description": "Liquid & Wash", "shade": "Keratin & Argan Oil",
                "size_volume": "400ml", "skin_type": "Frizzy & Treated Hair", "purchase_price": 1280.00, "sale_price": 1650.00,
                "discount": 0.00, "stock": 30, "reorder": 6, "unit": "Bottle", "batch_no": "TRS-PK2420",
                "expiry_date": today + timedelta(days=650), "supp": "Unilever Pakistan Distribution Network"
            },

            # ======================== 4. HAIR OIL ========================
            {
                "brand": "Bio Amla", "name": "Original Herbal Hair Oil 24 Natural Herbs", "barcode": "896101412021",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Classic Green Herbal",
                "size_volume": "200ml", "skin_type": "Dandruff & Hair Fall", "purchase_price": 210.00, "sale_price": 280.00,
                "discount": 0.00, "stock": 70, "reorder": 15, "unit": "Bottle", "batch_no": "BAM-PK2421",
                "expiry_date": today + timedelta(days=900), "supp": "Bio Amla & Forvil Cosmetics Ltd"
            },
            {
                "brand": "Bio Amla", "name": "Original Herbal Hair Oil Family Size", "barcode": "896101412022",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Classic Green Herbal",
                "size_volume": "400ml", "skin_type": "Dandruff & Hair Fall", "purchase_price": 390.00, "sale_price": 520.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Bottle", "batch_no": "BAM-PK2422",
                "expiry_date": today + timedelta(days=900), "supp": "Bio Amla & Forvil Cosmetics Ltd"
            },
            {
                "brand": "Dabur", "name": "Amla Hair Oil for Long Strong Black Hair", "barcode": "896101412023",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Original Indian Gooseberry",
                "size_volume": "200ml", "skin_type": "Premature Greying & Thinning", "purchase_price": 340.00, "sale_price": 450.00,
                "discount": 0.00, "stock": 55, "reorder": 12, "unit": "Bottle", "batch_no": "DAB-PK2423",
                "expiry_date": today + timedelta(days=850), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Dabur", "name": "Vatika Enriched Coconut Hair Oil with Henna & Amla", "barcode": "896101412024",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Henna Amla Lemon Triple Herbs",
                "size_volume": "300ml", "skin_type": "Dry & Damaged Hair", "purchase_price": 570.00, "sale_price": 750.00,
                "discount": 0.00, "stock": 40, "reorder": 8, "unit": "Bottle", "batch_no": "DAB-PK2424",
                "expiry_date": today + timedelta(days=820), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Parachute", "name": "100% Pure Coconut Hair Oil Deep Conditioning", "barcode": "896101412025",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "100% Edible Grade Pure Coconut",
                "size_volume": "200ml", "skin_type": "Dry Hair & Scalp Nourishment", "purchase_price": 370.00, "sale_price": 480.00,
                "discount": 0.00, "stock": 60, "reorder": 10, "unit": "Bottle", "batch_no": "PAR-PK2425",
                "expiry_date": today + timedelta(days=900), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Saeed Ghani", "name": "Mughziat Herbal Hair Oil Traditional Growth Formula", "barcode": "896101412026",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "Traditional Mughziat Extract",
                "size_volume": "120ml", "skin_type": "Hair Fall & Scalp Health", "purchase_price": 310.00, "sale_price": 420.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Bottle", "batch_no": "SGH-PK2426",
                "expiry_date": today + timedelta(days=700), "supp": "Saeed Ghani Herbal & Natural Products"
            },
            {
                "brand": "Marhaba", "name": "Pure Roghan Badam Shirin Almond Oil", "barcode": "896101412027",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "100% Pure Sweet Almond",
                "size_volume": "60ml", "skin_type": "Nourishing Scalp & Memory Care", "purchase_price": 440.00, "sale_price": 580.00,
                "discount": 0.00, "stock": 35, "reorder": 8, "unit": "Bottle", "batch_no": "MRH-PK2427",
                "expiry_date": today + timedelta(days=800), "supp": "Saeed Ghani Herbal & Natural Products"
            },
            {
                "brand": "L'Oreal Paris", "name": "Elvive Extraordinary Oil Multi-Use Hair Serum", "barcode": "896101412028",
                "category": "Hair Oils & Scalp Care", "description": "Oil & Serum", "shade": "6 Precious Flower Micro-Oils",
                "size_volume": "100ml", "skin_type": "Dry, Rough & Dull Hair", "purchase_price": 2250.00, "sale_price": 2950.00,
                "discount": 100.00, "stock": 20, "reorder": 4, "unit": "Pump Bottle", "batch_no": "LOR-PK2428",
                "expiry_date": today + timedelta(days=640), "supp": "L'Oreal & Garnier Consumer Supply Hub"
            },

            # ======================== 5. SUNSCREEN & SUNBLOCKS ========================
            {
                "brand": "U-Veil", "name": "U-Veil Forte Sunscreen Cream SPF 60 Water Resistant", "barcode": "896101412029",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 60 Broad Spectrum",
                "size_volume": "60g", "skin_type": "All Skin Types / Melasma Prone", "purchase_price": 650.00, "sale_price": 850.00,
                "discount": 0.00, "stock": 55, "reorder": 12, "unit": "Tube", "batch_no": "UVL-PK2429",
                "expiry_date": today + timedelta(days=580), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Solaris", "name": "Solaris Ultra Sunblock Anti-Aging SPF 60", "barcode": "896101412030",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 60 Non-Greasy",
                "size_volume": "60ml", "skin_type": "Sensitive & Pigmented Skin", "purchase_price": 720.00, "sale_price": 950.00,
                "discount": 0.00, "stock": 48, "reorder": 10, "unit": "Tube", "batch_no": "SOL-PK2430",
                "expiry_date": today + timedelta(days=620), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Vince", "name": "Sunblock Maximum Protection Non-Greasy SPF 75", "barcode": "896101412031",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 75 UVA/UVB Shield",
                "size_volume": "75ml", "skin_type": "Fair to Wheatish Skin", "purchase_price": 1080.00, "sale_price": 1450.00,
                "discount": 50.00, "stock": 38, "reorder": 8, "unit": "Tube", "batch_no": "VNC-PK2431",
                "expiry_date": today + timedelta(days=700), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Rivaj UK", "name": "Sun Block Whitening & Anti-Sebum SPF 60", "barcode": "896101412032",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 60 Anti-Darkening",
                "size_volume": "120ml", "skin_type": "Normal to Oily Skin", "purchase_price": 520.00, "sale_price": 680.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Tube", "batch_no": "RVJ-PK2432",
                "expiry_date": today + timedelta(days=640), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Jenpharm", "name": "Spectra Block Sunblock Non-Comedogenic SPF 60", "barcode": "896101412033",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 60 PA+++ Matte",
                "size_volume": "60g", "skin_type": "Acne-Prone & Sensitive Skin", "purchase_price": 1280.00, "sale_price": 1650.00,
                "discount": 0.00, "stock": 32, "reorder": 6, "unit": "Tube", "batch_no": "JNP-PK2433",
                "expiry_date": today + timedelta(days=580), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Neutrogena", "name": "Ultra Sheer Dry-Touch Sunblock SPF 50+ Helioplex", "barcode": "896101412034",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 50+ Broad Spectrum",
                "size_volume": "88ml", "skin_type": "All Skin Types / Matte Finish", "purchase_price": 2480.00, "sale_price": 3250.00,
                "discount": 100.00, "stock": 25, "reorder": 5, "unit": "Tube", "batch_no": "NTG-PK2434",
                "expiry_date": today + timedelta(days=620), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "La Roche-Posay", "name": "Anthelios UVMune 400 Invisible Fluid SPF 50+", "barcode": "896101412035",
                "category": "Sunscreens & Sunblocks", "description": "Sunscreen Spray / Fluid", "shade": "SPF 50+ Mexoryl 400 Ultra-Long",
                "size_volume": "50ml", "skin_type": "Sensitive, Fair & All Skin Types", "purchase_price": 5200.00, "sale_price": 6800.00,
                "discount": 0.00, "stock": 14, "reorder": 3, "unit": "Bottle", "batch_no": "LRP-PK2435",
                "expiry_date": today + timedelta(days=700), "supp": "Derma Tech & Skin Pharma Distributors"
            },
            {
                "brand": "Eveline", "name": "Sun Protection Face Cream Sunblock SPF 50 Mattifying", "barcode": "896101412036",
                "category": "Sunscreens & Sunblocks", "description": "Sunblock / SPF Shield", "shade": "SPF 50 High Protection Anti-Shine",
                "size_volume": "50ml", "skin_type": "All Skin Types", "purchase_price": 1680.00, "sale_price": 2200.00,
                "discount": 0.00, "stock": 6, "reorder": 8, "unit": "Tube", "batch_no": "EVL-PK2436",
                "expiry_date": today + timedelta(days=400), "supp": "Derma Tech & Skin Pharma Distributors"
            },

            # ======================== 6. HAND CREAMS ========================
            {
                "brand": "Nivea", "name": "Nivea Soft Refreshingly Soft Moisturizing Cream", "barcode": "896101412037",
                "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Jojoba Oil & Vitamin E",
                "size_volume": "100ml", "skin_type": "Hands, Face & Body", "purchase_price": 490.00, "sale_price": 650.00,
                "discount": 0.00, "stock": 48, "reorder": 10, "unit": "Jar", "batch_no": "NIV-PK2437",
                "expiry_date": today + timedelta(days=700), "supp": "Beiersdorf Pakistan (Nivea Supply)"
            },
            {
                "brand": "Vaseline", "name": "Intensive Care Healthy Hands & Stronger Nails", "barcode": "896101412038",
                "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Keratin & Vaseline Jelly",
                "size_volume": "75ml", "skin_type": "Dry Hands & Brittle Nails", "purchase_price": 420.00, "sale_price": 550.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Tube", "batch_no": "VAS-PK2438",
                "expiry_date": today + timedelta(days=650), "supp": "Unilever Pakistan Distribution Network"
            },
            {
                "brand": "Neutrogena", "name": "Norwegian Formula Concentrated Hand Cream", "barcode": "896101412039",
                "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Glycerin Rich Fragrance-Free",
                "size_volume": "50ml", "skin_type": "Severely Chapped Hands", "purchase_price": 1250.00, "sale_price": 1650.00,
                "discount": 0.00, "stock": 25, "reorder": 5, "unit": "Tube", "batch_no": "NTG-PK2439",
                "expiry_date": today + timedelta(days=680), "supp": "Muller & Phipps Pakistan (Pvt) Ltd"
            },
            {
                "brand": "Saeed Ghani", "name": "Sandalwood Natural Hand & Foot Cream", "barcode": "896101412040",
                "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Pure Sandalwood Extract",
                "size_volume": "60ml", "skin_type": "Dry Hands & Cracked Heels", "purchase_price": 240.00, "sale_price": 320.00,
                "discount": 0.00, "stock": 45, "reorder": 10, "unit": "Jar", "batch_no": "SGH-PK2440",
                "expiry_date": today + timedelta(days=500), "supp": "Saeed Ghani Herbal & Natural Products"
            },
            {
                "brand": "Golden Pearl", "name": "Soft & White Hand & Foot Whitening Cream", "barcode": "896101412041",
                "category": "Hand Creams & Lotions", "description": "Cream & Lotion", "shade": "Herbal Glow Blend",
                "size_volume": "60ml", "skin_type": "Dark & Dry Knuckles", "purchase_price": 260.00, "sale_price": 350.00,
                "discount": 0.00, "stock": 50, "reorder": 10, "unit": "Jar", "batch_no": "GDP-PK2441",
                "expiry_date": today + timedelta(days=520), "supp": "Bio Amla & Forvil Cosmetics Ltd"
            },
        ]

        item_records = []
        for p in products:
            item = db.query(Item).filter(Item.barcode == p["barcode"]).first()
            if not item:
                item = Item(
                    item_code=next_code(db, Item, "item_code", "SKU"),
                    brand=p["brand"],
                    name=p["name"],
                    barcode=p["barcode"],
                    category=p["category"],
                    description=p["description"],
                    shade=p["shade"],
                    size_volume=p["size_volume"],
                    skin_type=p["skin_type"],
                    purchase_price=Decimal(str(p["purchase_price"])),
                    sale_price=Decimal(str(p["sale_price"])),
                    discount=Decimal(str(p["discount"])),
                    current_stock=p["stock"],
                    reserved_stock=0,
                    reorder_level=p["reorder"],
                    unit=p["unit"],
                    batch_no=p["batch_no"],
                    expiry_date=p["expiry_date"],
                    status="Active"
                )
                db.add(item)
                db.flush()

                # Add initial stock movement
                db.add(StockMovement(
                    item_id=item.id,
                    movement_type="purchase",
                    quantity_change=p["stock"],
                    quantity_after=p["stock"],
                    note="Initial warehouse stock received from distributor"
                ))
            item_records.append(item)

        # 8. Create Purchase Bills & Supplier Invoices
        unilever = supplier_map.get("Unilever Pakistan Distribution Network")
        if unilever:
            unilever_items = [it for it in item_records if it.brand in ["Pond's", "Dove", "Lifebuoy", "Sunsilk", "Lux", "Vaseline"]][:4]
            if unilever_items:
                tot_p = sum(it.purchase_price * 10 for it in unilever_items)
                paid_p = tot_p * Decimal("0.7")
                inv_no = next_code(db, Purchase, "invoice_no", "PUR")
                p_bill = Purchase(
                    invoice_no=inv_no,
                    supplier_id=unilever.id,
                    date=today - timedelta(days=5),
                    total_amount=tot_p,
                    amount_paid=paid_p,
                    balance=tot_p - paid_p,
                    payment_method="Bank Transfer",
                    note="Commercial replenishment - Sunsilk, Pond's & Dove personal care"
                )
                db.add(p_bill)
                db.flush()

                for it in unilever_items:
                    db.add(PurchaseItem(
                        purchase_id=p_bill.id,
                        item_id=it.id,
                        quantity=10,
                        unit_price=it.purchase_price,
                        subtotal=it.purchase_price * 10
                    ))

                # Supplier Ledger entry
                add_supplier_ledger(
                    db, unilever, today - timedelta(days=5),
                    f"Purchase Bill #{inv_no} (Replenishment)",
                    debit=tot_p - paid_p, credit=Decimal("0"),
                    reference_type="purchase", reference_id=p_bill.id
                )

        # 9. Create Real POS Sales Transactions
        # Sale 1: Walk-in counter cash sale
        walkin_items = [it for it in item_records if it.brand in ["Himalaya", "Lifebuoy", "Head & Shoulders", "U-Veil"]][:3]
        if walkin_items:
            s_tot = sum(it.sale_price for it in walkin_items)
            inv_s1 = next_code(db, Sale, "invoice_no", "INV")
            sale1 = Sale(
                invoice_no=inv_s1,
                customer_id=walk_in.id,
                date=today,
                total_amount=s_tot,
                amount_received=s_tot,
                balance=0,
                payment_method="Cash",
                note="Walk-in counter retail checkout"
            )
            db.add(sale1)
            db.flush()

            for it in walkin_items:
                db.add(SaleItem(
                    sale_id=sale1.id,
                    item_id=it.id,
                    quantity=1,
                    unit_price=it.sale_price,
                    subtotal=it.sale_price
                ))
                apply_stock_change(db, it, -1, "sale", reference_type="sale", reference_id=sale1.id, note="POS Cash Sale")

        # Sale 2: Dr. Farhana Aesthetics clinic purchase (Credit account)
        clinic = customer_map.get("Dr. Farhana Skin & Aesthetics Clinic")
        if clinic:
            sun_items = [it for it in item_records if it.category == "Sunscreens & Sunblocks"][:2]
            if sun_items:
                s2_tot = sum(it.sale_price * 2 for it in sun_items)
                s2_paid = s2_tot * Decimal("0.5") # Partial advance
                inv_s2 = next_code(db, Sale, "invoice_no", "INV")
                sale2 = Sale(
                    invoice_no=inv_s2,
                    customer_id=clinic.id,
                    date=today - timedelta(days=2),
                    total_amount=s2_tot,
                    amount_received=s2_paid,
                    balance=s2_tot - s2_paid,
                    payment_method="Bank Transfer",
                    note="Clinical supply - Sun protection & post-procedure care"
                )
                db.add(sale2)
                db.flush()

                for it in sun_items:
                    db.add(SaleItem(
                        sale_id=sale2.id,
                        item_id=it.id,
                        quantity=2,
                        unit_price=it.sale_price,
                        subtotal=it.sale_price * 2
                    ))
                    apply_stock_change(db, it, -2, "sale", reference_type="sale", reference_id=sale2.id, note="Clinical Order")

                # Customer Ledger
                add_customer_ledger(
                    db, clinic, today - timedelta(days=2),
                    f"Invoice #{inv_s2} - Sun protection supply",
                    debit=s2_tot - s2_paid, credit=Decimal("0"),
                    reference_type="sale", reference_id=sale2.id
                )

        db.commit()
        print("\n" + "=" * 60)
        print("SUCCESSFULLY SEEDED PAKISTAN MARKET DATA FOR AHMAD SHOP!")
        print("=" * 60)
        print(f"Categories in Store:    {db.query(ItemCategory).count()}")
        print(f"Total Products Seeded:  {db.query(Item).count()} items")
        print(f"Pakistani Suppliers:    {db.query(Supplier).count()} distributors")
        print(f"Customers / Accounts:   {db.query(Customer).count()} profiles")
        print(f"Completed Sales:        {db.query(Sale).count()} transactions")
        print(f"Purchase Invoices:      {db.query(Purchase).count()} orders")
        print("=" * 60)

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_pakistan_data()
