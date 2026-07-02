from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def init_db():
    from models import User, Category, Product, ProductImage, HeroSlide, AffiliateClick, SocialLink, Platform, UserLink
    Base.metadata.create_all(bind=engine)
