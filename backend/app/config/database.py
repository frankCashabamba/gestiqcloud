
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

Base = declarative_base()

def make_db_url() -> str:
    # Ya es str y viene normalizada desde Settings.database_url
    url = settings.database_url
    if settings.ENV == "production" and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

engine = create_engine(make_db_url(), pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
