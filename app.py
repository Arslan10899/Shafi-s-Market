import os
from flask import Flask

from config import SECRET_KEY
from database import init_db
from templates import social_links_context

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2592000

from routers import auth, products, admin, dashboard, profile
app.register_blueprint(auth.bp)
app.register_blueprint(products.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(profile.bp)

app.context_processor(social_links_context)

init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
