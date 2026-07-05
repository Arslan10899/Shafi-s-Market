import os
import random
import string
import time as time_module
from slugify import slugify
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, prefix="prod"):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"{prefix}_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"


def gen_slug(text):
    base = slugify(text)[:200]
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}-{suffix}"


def save_image(file, prefix="msg"):
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
    filename = f"{prefix}_{random.randint(10000,99999)}_{int(time_module.time())}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)
    return f"/static/uploads/{filename}"
