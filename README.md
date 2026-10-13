# Ahmad Cosmetics — Store Operations & Management System

A production-grade, fast, and responsive Point of Sale (POS), Inventory, and Accounting ERP built for retail and wholesale cosmetics operations (facewash, body wash, shampoo, hair oil, sunscreen, hand creams, and sun blocks).

Designed with a modern, gender-neutral palette (Deep Navy, Accent Teal, Crisp White, and Neutral Slate) for shopkeepers, staff, and customers.

---

## Key Features

- **Point of Sale (POS):**
  - Ultra-fast product search with barcode scan support.
  - Walk-in and credit customer checkout.
  - Multi-payment support: Cash, Bank Transfer, and Account Credit.
  - Printable 80mm thermal receipts and formal A4 invoices.
- **Pending Pre-Orders & Reservation Management:**
  - Customer order reservations with advance deposits.
  - Multi-status tracking: Pending, Confirmed, Preparing, Ready for Collection, Out for Delivery, Partially Fulfilled, Completed, Cancelled.
  - Automatic inventory reservation and release on dispatch or cancellation.
- **Cosmetics Inventory Management:**
  - SKU, barcode, formulation texture, SPF rating, and shade/variant attributes.
  - Batch number tracking and automated expiry detection (blocks expired items at POS).
  - Low-stock alerts and safety reorder thresholds.
  - Complete chronological stock movement history.
- **Supplier Procurement & Accounts Payable:**
  - Purchase bill entry with automatic stock incrementing.
  - Supplier running ledgers and payment disbursals.
  - Supplier returns with inventory deduction.
- **Customer Accounts & Receivables:**
  - Double-entry running balance ledgers (debits, credits, invoices, payments).
  - Walk-in customer instant checkout guarantee.
  - Customer returns with inventory restock.
- **Financial Accounting & Reporting:**
  - Daily Cash Book tracking cash receipts and payouts.
  - Profit & Loss statement based on commercial sales margin.
  - Stock asset valuation (FIFO cost basis).
  - Outstanding balances and aging analysis.
- **Security & Staff Access:**
  - Role-based permissions (Administrator, Cashier).
  - Password hashing via bcrypt.
  - Brute-force throttling and lockouts.
  - Immutable audit trail.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.10+, FastAPI |
| **ASGI Server** | Uvicorn |
| **Database** | SQLAlchemy (SQLite / MySQL) |
| **Templating** | Jinja2 |
| **Frontend Styling**| Custom Vanilla CSS Design System |
| **Icons** | Lucide Icons |
| **Analytics** | Chart.js |

---

## Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone Repository
```bash
git clone https://github.com/MSaad1212/Ahmad-Cosmetics-.git
cd Ahmad-Cosmetics-
```

### 3. Create and Activate Virtual Environment
```bash
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Variables
Create a `.env` file in the project root:
```env
DB_URL=sqlite:///./ahmad_shop.db
SECRET_KEY=your-super-secret-key-change-this-in-production
PORT=8000
```

### 6. Run the Application
```bash
python run.py
```
Open your browser and navigate to: **`http://localhost:8000`**

### Default Administrator Credentials
- **Username:** `admin`
- **Password:** `admin123`

---

## Seed Dummy / Pakistan Market Data

To populate sample Pakistani cosmetic inventory, suppliers, customers, and sales:
```bash
python seed_pakistan_market_data.py
```

---

## License & Author

Developed for **Ahmad Cosmetics Shop**. All rights reserved.
