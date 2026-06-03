from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# PostgreSQL болон SQLite хоёуланг дэмжинэ
_db_url = settings.DATABASE_URL

if _db_url.startswith("postgres://"):
    # Render нь postgres:// гэж өгдөг, SQLAlchemy postgresql:// шаарддаг
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

# SQLite бол check_same_thread нэмнэ, PostgreSQL-д хэрэггүй
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(_db_url, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
