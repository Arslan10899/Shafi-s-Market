import os
from datetime import datetime
from flask import Flask, session
from sqlalchemy.orm import joinedload

from config import SECRET_KEY, CURRENCIES
from database import init_db, get_db
from models import Message
from templates import social_links_context

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2592000

from routers import auth, products, admin, dashboard, profile, blog, messages
app.register_blueprint(auth.bp)
app.register_blueprint(products.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(profile.bp)
app.register_blueprint(blog.bp)
app.register_blueprint(messages.bp)

def inject_globals():
    return dict(CURRENCIES=CURRENCIES)

def price_parts(price):
    s = "{:,.2f}".format(price)
    if "." in s:
        a, b = s.rsplit(".", 1)
        return {"int": a, "dec": b}
    return {"int": s, "dec": "00"}
app.jinja_env.globals["price_parts"] = price_parts

app.context_processor(social_links_context)
app.context_processor(inject_globals)

@app.before_request
def track_activity():
    uid = session.get("user_id")
    if uid:
        from database import SessionLocal
        from models import User
        db = SessionLocal()
        db.query(User).filter(User.id == uid).update({"last_seen": datetime.utcnow()})
        db.commit()
        db.close()

init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
