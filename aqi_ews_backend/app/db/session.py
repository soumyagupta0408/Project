from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

db_url = settings.get_database_url()

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "connect_args": {"connect_timeout": 5},
}

if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_recycle": 1800,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_engine(db_url, **engine_kwargs)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()