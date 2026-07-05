from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    return SessionLocal()


def init_db():
    from models import User, Category, Product, ProductImage, HeroSlide, AffiliateClick, SocialLink, Platform, UserLink, BlogPost, Message, SiteSetting
    Base.metadata.create_all(bind=engine)
    # Add currency column if missing (migration)
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('products')]
    if 'currency' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN currency VARCHAR(10) DEFAULT 'USD'"))
            conn.commit()
    if 'is_active' not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.commit()
    cols2 = [c['name'] for c in inspector.get_columns('user_links')]
    if 'category_id' not in cols2:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE user_links ADD COLUMN category_id INTEGER REFERENCES categories(id)"))
            conn.commit()
    if 'image' not in cols2:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE user_links ADD COLUMN image VARCHAR(300) DEFAULT ''"))
            conn.commit()
    cols3 = [c['name'] for c in inspector.get_columns('products')]
    if 'user_id' not in cols3:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            conn.commit()
    ucols = [c['name'] for c in inspector.get_columns('users')]
    if 'last_seen' not in ucols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_seen TIMESTAMP"))
            conn.commit()
    mcols = [c['name'] for c in inspector.get_columns('messages')]
    if 'status' not in mcols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN status VARCHAR(20) DEFAULT 'sent'"))
            conn.commit()
    ucols2 = [c['name'] for c in inspector.get_columns('users')]
    if 'is_blocked' not in ucols2:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0"))
            conn.commit()
