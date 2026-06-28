from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL, IS_SQLITE, IS_MYSQL

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
elif IS_MYSQL:
    engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20, pool_pre_ping=True, connect_args={"charset": "utf8mb4"})
else:
    engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import User, Category, Product, ProductImage, HeroSlide, AffiliateClick
    Base.metadata.create_all(bind=engine)
