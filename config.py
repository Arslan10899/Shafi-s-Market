import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'affiliate.db')
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

_sk = os.environ.get("SECRET_KEY")
if not _sk:
    _sk_file = os.path.join(BASE_DIR, '.secret_key')
    if os.path.isfile(_sk_file):
        _sk = open(_sk_file).read().strip()
    else:
        _sk = secrets.token_hex(32)
        try:
            with open(_sk_file, 'w') as f:
                f.write(_sk)
        except OSError:
            pass
SECRET_KEY = _sk
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "static", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar"},
    "PKR": {"symbol": "₨", "name": "Pakistani Rupee"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
    "INR": {"symbol": "₹", "name": "Indian Rupee"},
    "BDT": {"symbol": "৳", "name": "Bangladeshi Taka"},
    "AED": {"symbol": "د.إ", "name": "UAE Dirham"},
    "SAR": {"symbol": "﷼", "name": "Saudi Riyal"},
}

AFFILIATE_PLATFORMS = {
    "amazon": {"name": "Amazon", "icon": "fab fa-amazon", "color": "#FF9900"},
    "alibaba": {"name": "Alibaba", "icon": "fas fa-globe", "color": "#FF6A00"},
    "aliexpress": {"name": "AliExpress", "icon": "fas fa-shopping-bag", "color": "#E62E04"},
    "daraz": {"name": "Daraz", "icon": "fas fa-store", "color": "#FF7A00"},
}
