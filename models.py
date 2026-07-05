from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(100), default="")
    profile_image = Column(String(300), default="")
    bio = Column(Text, default="")
    phone = Column(String(30), default="")
    website = Column(String(300), default="")
    storage_used_mb = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    role = Column(String(50), default="affiliate")
    created_at = Column(DateTime, server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    image = Column(String(300), default="")
    created_at = Column(DateTime, server_default=func.now())

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(250), unique=True, nullable=False, index=True)
    short_description = Column(String(300), default="")
    description = Column(Text, default="")
    image = Column(String(300), default="")
    price = Column(Float, nullable=True)
    old_price = Column(Float, nullable=True)
    rating = Column(Float, default=0)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    currency = Column(String(10), default="USD")
    is_active = Column(Boolean, default=True)
    affiliate_platform = Column(String(30), nullable=False)
    affiliate_url = Column(String(500), nullable=False)
    is_featured = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    owner = relationship("User", backref="products")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(300), nullable=False)
    sort_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")


class HeroSlide(Base):
    __tablename__ = "hero_slides"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(300), default="")
    image_url = Column(String(500), nullable=False)
    btn_text = Column(String(100), default="Shop Now")
    btn_url = Column(String(300), default="/shop")
    btn_type = Column(String(20), default="primary")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(30), nullable=False)
    clicked_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(50), default="")
    user_agent = Column(String(300), default="")


class SocialLink(Base):
    __tablename__ = "social_links"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False)
    icon = Column(String(50), default="fas fa-link")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(100), default="fas fa-shopping-cart")
    base_url = Column(String(300), default="")
    is_active = Column(Boolean, default=True)


class UserLink(Base):
    __tablename__ = "user_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    url = Column(String(500), nullable=False)
    title = Column(String(200), default="")
    description = Column(Text, default="")
    image = Column(String(300), default="")
    clicks_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="links")
    platform = relationship("Platform")
    category = relationship("Category")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, default="")
    image = Column(String(300), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(String(300), default="")
    image = Column(String(300), default="")
    author = Column(String(100), default="Admin")
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
