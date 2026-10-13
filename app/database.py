import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import urlparse

load_dotenv()

# Detect Vercel / serverless environment
is_vercel = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url:
    if is_vercel:
        # On Vercel serverless, root directory is read-only; /tmp is the only writable directory.
        DATABASE_URL = "sqlite:////tmp/ahmad_shop.db"
    else:
        # Local development default
        DATABASE_URL = "mysql+pymysql://root:@localhost:3306/ahmad_shop"
else:
    DATABASE_URL = raw_db_url

# Standardize postgres dialect prefix for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Auto-create database ONLY for local MySQL development (do not attempt on cloud providers or Vercel)
try:
    url = urlparse(DATABASE_URL)
    if url.scheme in ["mysql", "mysql+pymysql"]:
        host = url.hostname or "localhost"
        if host in ["localhost", "127.0.0.1"] and not is_vercel:
            import pymysql
            user = url.username or "root"
            password = url.password or ""
            port = url.port or 3306
            db_name = url.path.lstrip("/")
            
            if db_name:
                conn = pymysql.connect(host=host, user=user, password=password, port=port)
                cursor = conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                conn.close()
except Exception as e:
    print(f"Notice: Database auto-creation check skipped: {e}")

# Build engine with dialect-appropriate pooling & thread parameters
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Vital for cloud databases & serverless functions to survive connection drops
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
