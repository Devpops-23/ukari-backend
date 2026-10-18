from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

connect_args = {"check_same_thread": False} if (DATABASE_URL and DATABASE_URL.startswith("sqlite")) else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_migrations(engine):
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            if engine.dialect.name == "sqlite":
                for table, cols in [
                    ("trips", [
                        ("travel_date", "DATETIME"),
                        ("max_weight", "FLOAT DEFAULT 20.0"),
                        ("status", "VARCHAR DEFAULT 'active'"),
                        ("total_earned", "FLOAT DEFAULT 0.0"),
                    ]),
                    ("orders", [
                        ("store_name", "VARCHAR DEFAULT 'walmart'"),
                        ("pickup_location", "VARCHAR DEFAULT ''"),
                        ("delivery_location", "VARCHAR DEFAULT ''"),
                        ("item_price", "FLOAT DEFAULT 0.0"),
                        ("platform_fee", "FLOAT DEFAULT 0.0"),
                        ("traveler_fee", "FLOAT DEFAULT 0.0"),
                        ("total_charged", "FLOAT DEFAULT 0.0"),
                        ("amount_earned", "FLOAT DEFAULT 0.0"),
                        ("traveler_arrived_at", "DATETIME"),
                        ("delivery_deadline", "DATETIME"),
                        ("package_received_at", "DATETIME"),
                        ("proof_photo_url", "VARCHAR"),
                        ("dispute_reason", "VARCHAR"),
                        ("disputed_at", "DATETIME"),
                        ("dispute_status", "VARCHAR"),
                        ("dispute_created_at", "DATETIME"),
                        ("refunded_at", "DATETIME"),
                    ]),
                ]:
                    res = conn.execute(text(f"PRAGMA table_info({table})"))
                    existing = {row[1] for row in res.fetchall()}
                    for col, col_type in cols:
                        if col not in existing:
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
    except Exception as e:
        print(f"Schema migration note: {e}")



