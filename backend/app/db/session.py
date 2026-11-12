import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings

def get_engine(database_url: str = None):
    url = database_url or settings.DATABASE_URL
    # Handle SQLite thread checking if used in testing or dev fallback
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(
        url,
        echo=settings.SQL_ECHO,
        connect_args=connect_args,
        pool_pre_ping=True
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

