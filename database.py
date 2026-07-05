from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    return SessionLocal()


def _missing_cols(table):
    return {c['name'] for c in inspect(engine).get_columns(table)}


def _add_col(table, col_def):
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
        conn.commit()


_MIGRATIONS = [
    ("products", "currency", "VARCHAR(10) DEFAULT 'USD'"),
    ("products", "is_active", "BOOLEAN DEFAULT 1"),
    ("products", "user_id", "INTEGER REFERENCES users(id)"),
    ("user_links", "category_id", "INTEGER REFERENCES categories(id)"),
    ("user_links", "image", "VARCHAR(300) DEFAULT ''"),
    ("users", "last_seen", "TIMESTAMP"),
    ("users", "is_blocked", "BOOLEAN DEFAULT 0"),
    ("messages", "status", "VARCHAR(20) DEFAULT 'sent'"),
]


def init_db():
    from models import User, Category, Product, ProductImage, HeroSlide, AffiliateClick, SocialLink, Platform, UserLink, BlogPost, Message, SiteSetting
    Base.metadata.create_all(bind=engine)
    for table, col, col_def in _MIGRATIONS:
        if col not in _missing_cols(table):
            _add_col(table, col_def)

    if 'receiver_id' not in _missing_cols('messages'):
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            conn.execute(text("""CREATE TABLE messages_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                content TEXT DEFAULT '', image VARCHAR(300) DEFAULT '',
                is_read BOOLEAN DEFAULT 0, status VARCHAR(20) DEFAULT 'sent',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
            conn.execute(text("INSERT INTO messages_new SELECT * FROM messages"))
            conn.execute(text("DROP TABLE messages"))
            conn.execute(text("ALTER TABLE messages_new RENAME TO messages"))
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()
