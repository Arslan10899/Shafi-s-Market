import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'affiliate.db')
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production-2025-affiliate")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "static", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

AFFILIATE_PLATFORMS = {
    "amazon": {"name": "Amazon", "icon": "fab fa-amazon", "color": "#FF9900"},
    "alibaba": {"name": "Alibaba", "icon": "fas fa-globe", "color": "#FF6A00"},
    "aliexpress": {"name": "AliExpress", "icon": "fas fa-shopping-bag", "color": "#E62E04"},
    "daraz": {"name": "Daraz", "icon": "fas fa-store", "color": "#FF7A00"},
}
