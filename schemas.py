from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str = "affiliate"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    image: str = ""


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    image: str
    product_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    short_description: str = ""
    description: str = ""
    image: str = ""
    price: Optional[float] = None
    old_price: Optional[float] = None
    rating: float = 0
    category_id: Optional[int] = None
    affiliate_platform: str = Field(pattern="^(amazon|alibaba|aliexpress|daraz)$")
    affiliate_url: str = Field(min_length=1)
    is_featured: bool = False
    is_new: bool = False


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = None
    old_price: Optional[float] = None
    rating: Optional[float] = None
    category_id: Optional[int] = None
    affiliate_platform: Optional[str] = None
    affiliate_url: Optional[str] = None
    is_featured: Optional[bool] = None
    is_new: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    title: str
    slug: str
    short_description: str
    description: str
    image: str
    price: Optional[float] = None
    old_price: Optional[float] = None
    rating: float
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    affiliate_platform: str
    affiliate_url: str
    is_featured: bool
    is_new: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
