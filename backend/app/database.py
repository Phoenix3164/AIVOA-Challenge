from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_investigation_columns() -> None:
    """Bring the local SQLite demo database forward without modifying user data.

    Production deployments should run Alembic; this small compatibility step lets
    an existing out-of-box SQLite file gain the added nullable columns on startup.
    """
    required = {
        "manufacturing_date": "VARCHAR(80)",
        "department": "VARCHAR(160)",
        "incident_category": "VARCHAR(160)",
        "batch_disposition": "TEXT",
    }
    columns = {column["name"] for column in inspect(engine).get_columns("investigations")}
    with engine.begin() as connection:
        for name, sql_type in required.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE investigations ADD COLUMN {name} {sql_type}"))
