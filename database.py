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
    # Make receiver_id nullable in messages table (for drafts without recipient)
    with engine.connect() as conn:
        row = conn.execute(text("PRAGMA table_info(messages)")).fetchall()
        receiver_nullable = any(r[1] == 'receiver_id' and r[3] == 0 for r in row)
        if r := next((r for r in row if r[1] == 'receiver_id'), None):
            if r[3] == 0:  # notnull = 0 means nullable, but in PRAGMA output column 4 (index 3) is 'notnull', 0 means nullable... wait
                pass
        # Actually in PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
        # notnull=0 means nullable, notnull=1 means NOT NULL
        # So we want to fix if notnull == 1
        receiver_col = next((r for r in row if r[1] == 'receiver_id'), None)
        if receiver_col and receiver_col[3] == 1:  # notnull == 1 means NOT NULL
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            conn.execute(text("CREATE TABLE messages_new (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE, content TEXT DEFAULT '', image VARCHAR(300) DEFAULT '', is_read BOOLEAN DEFAULT 0, status VARCHAR(20) DEFAULT 'sent', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
            conn.execute(text("INSERT INTO messages_new SELECT * FROM messages"))
            conn.execute(text("DROP TABLE messages"))
            conn.execute(text("ALTER TABLE messages_new RENAME TO messages"))
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()
