from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from datetime import datetime, timedelta
import os, random, string, jinja2

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'shafi-shop-fixed-dev-key-2025!@#')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
csrf = CSRFProtect(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "database", "ecommerce.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# ====== MODELS ======
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    address = db.Column(db.Text, default='')
    profile_image = db.Column(db.String(200), default='')
    role = db.Column(db.String(20), default='User')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    wishlist_items = db.relationship('Wishlist', backref='user', lazy=True)
    cart_items = db.relationship('Cart', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='category', lazy=True)
    subcategories = db.relationship('SubCategory', backref='category', lazy=True, cascade='all, delete-orphan')

class SubCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    image = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='subcategory', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('sub_category.id'), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    is_best = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Integer, default=0)
    brand = db.Column(db.String(100))
    specifications = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='product', lazy=True)
    wishlist_items = db.relationship('Wishlist', backref='product', lazy=True)
    cart_items = db.relationship('Cart', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    total_amount = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.Text)
    billing_address = db.Column(db.Text)
    shipping_method = db.Column(db.String(50))
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='Pending')
    coupon_code = db.Column(db.String(50))
    discount_amount = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    tracking_number = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    payment = db.relationship('Payment', backref='order', uselist=False, lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='Pending')
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, default=0)
    max_uses = db.Column(db.Integer, default=100)
    max_uses_per_user = db.Column(db.Integer, default=1)
    current_uses = db.Column(db.Integer, default=0)
    expiry_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CouponUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    ticket_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    author = db.Column(db.String(100))
    image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blog = db.relationship('Blog', backref='comments', lazy=True)
    user = db.relationship('User', backref='blog_comments', lazy=True)

class BlogRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    blog = db.relationship('Blog', backref='ratings', lazy=True)
    user = db.relationship('User', backref='blog_ratings', lazy=True)
    __table_args__ = (db.UniqueConstraint('blog_id', 'user_id'),)

def migrate_db():
    """Add missing columns/tables to existing database."""
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    if 'sub_category' not in tables:
        SubCategory.__table__.create(db.engine)
    if 'sub_category' in tables:
        cols = [c['name'] for c in inspector.get_columns('sub_category')]
        if 'image' not in cols:
            db.session.execute(db.text('ALTER TABLE sub_category ADD COLUMN image VARCHAR(200) DEFAULT \'\''))
            db.session.commit()
    if 'product' in tables:
        cols = [c['name'] for c in inspector.get_columns('product')]
        if 'subcategory_id' not in cols:
            db.session.execute(db.text('ALTER TABLE product ADD COLUMN subcategory_id INTEGER REFERENCES sub_category(id)'))
            db.session.commit()
    if 'coupon' in tables:
        cols = [c['name'] for c in inspector.get_columns('coupon')]
        if 'max_uses_per_user' not in cols:
            db.session.execute(db.text('ALTER TABLE coupon ADD COLUMN max_uses_per_user INTEGER DEFAULT 1'))
            db.session.commit()
    if 'coupon_usage' not in tables:
        CouponUsage.__table__.create(db.engine)

def is_base64_encoded(s):
    """Check if string is valid base64 encoding (old password format)."""
    import base64
    try:
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except Exception:
        return False

def migrate_passwords():
    """Migrate old base64-encoded passwords to werkzeug hashes."""
    users = User.query.all()
    for user in users:
        pwd = user.password
        if pwd and is_base64_encoded(pwd):
            import base64
            plain = base64.b64decode(pwd).decode()
            user.password = generate_password_hash(plain)
    db.session.commit()

with app.app_context():
    db.create_all()
    migrate_db()
    migrate_passwords()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@admin.com',
            password=generate_password_hash('admin123'), is_admin=True, role='Admin')
        db.session.add(admin)
        db.session.commit()

# ====== HELPERS ======
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def get_cart_count():
    if 'user_id' in session:
        cart_items = Cart.query.filter_by(user_id=session['user_id']).count()
        return cart_items
    return 0

def get_wishlist_count():
    if 'user_id' in session:
        return Wishlist.query.filter_by(user_id=session['user_id']).count()
    return 0

def gen_order_number():
    return 'ORD' + ''.join(random.choices(string.digits, k=8))

def gen_ticket():
    return 'TKT' + ''.join(random.choices(string.digits, k=6))

# ====== THEME SWITCHING ======
class ThemeLoader(jinja2.BaseLoader):
    def __init__(self, app):
        self.app = app
        self.default_loader = app.jinja_loader

    def get_source(self, environment, template):
        if template.startswith('modern/') or template.startswith('admin_'):
            return self.default_loader.get_source(environment, template)

        try:
            # Check if modern theme is active via session (available during request)
            theme = 'default'
            try:
                from flask import request
                theme = request.args.get('theme') or session.get('theme') or 'default'
            except Exception:
                pass

            if theme == 'modern':
                try:
                    return self.default_loader.get_source(environment, 'modern/' + template)
                except jinja2.TemplateNotFound:
                    pass
        except Exception:
            pass

        return self.default_loader.get_source(environment, template)

    def list_templates(self):
        return self.default_loader.list_templates()

app.jinja_loader = ThemeLoader(app)

@app.route('/theme/<theme>')
def switch_theme(theme):
    if theme in ('default', 'modern'):
        session['theme'] = theme
    return redirect(request.referrer or url_for('home'))

app.jinja_env.globals.update(min=min, max=max)

@app.context_processor
def inject_counts():
    return dict(
        cart_count=get_cart_count(),
        wishlist_count=get_wishlist_count(),
        categories=Category.query.all(),
        theme=session.get('theme', 'default')
    )

# ====== AUTH ROUTES ======
@app.route('/')
def home():
    featured = Product.query.filter_by(is_featured=True).limit(4).all()
    new_arrivals = Product.query.filter_by(is_new=True).limit(4).all()
    best_sellers = Product.query.filter_by(is_best=True).limit(4).all()
    flash_products = Product.query.filter(Product.discount > 0).limit(4).all()
    reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    return render_template('index.html',
        featured=featured, new_arrivals=new_arrivals,
        best_sellers=best_sellers, flash_products=flash_products,
        reviews=reviews)

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful!'})
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
@csrf.exempt
def register():
    data = request.get_json(silent=True) or request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if User.query.filter_by(username=username).first():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        flash('Username already exists', 'danger')
        return redirect(url_for('login'))
    if User.query.filter_by(email=email).first():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        flash('Email already registered', 'danger')
        return redirect(url_for('login'))
    new_user = User(username=username, email=email, password=generate_password_hash(password))
    db.session.add(new_user)
    db.session.commit()
    if request.is_json:
        return jsonify({'success': True, 'message': 'Account created successfully!'})
    flash('Account created! You can now login.', 'success')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
@csrf.exempt
def forgot_password():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Password reset link sent to your email!', 'success')
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Email not found'}), 404
    return render_template('forgot_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ====== USER DASHBOARD ======
@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(5).all()
    wishlist_count = Wishlist.query.filter_by(user_id=user.id).count()
    cart_count = Cart.query.filter_by(user_id=user.id).count()
    total_orders = Order.query.filter_by(user_id=user.id).count()
    return render_template('dashboard.html', user=user, orders=orders,
        wishlist_count=wishlist_count, cart_count=cart_count,
        total_orders=total_orders)

# ====== SHOP / PRODUCT LISTING ======
@app.route('/shop')
def shop():
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    subcategory_id = request.args.get('subcategory', type=int)
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search', '')
    brand = request.args.get('brand', '')
    rating = request.args.get('rating', type=int)

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if subcategory_id:
        query = query.filter_by(subcategory_id=subcategory_id)
    if search:
        query = query.filter(Product.name.contains(search))
    if brand:
        query = query.filter_by(brand=brand)
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    if rating:
        query = query.filter(Product.id.in_(
            db.session.query(Review.product_id).filter(Review.rating >= rating)))

    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'name':
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.all()
    brands = db.session.query(Product.brand).distinct().all()
    selected_category = Category.query.get(category_id) if category_id else None
    selected_subcategory = SubCategory.query.get(subcategory_id) if subcategory_id else None
    subcategories = SubCategory.query.filter_by(category_id=category_id).all() if category_id else []
    return render_template('shop.html', products=products, categories=categories,
        brands=[b[0] for b in brands if b[0]], selected_category=selected_category,
        selected_subcategory=selected_subcategory, subcategories=subcategories)

# ====== PRODUCT DETAIL ======
@app.route('/product/<int:pid>')
def product_detail(pid):
    product = Product.query.get_or_404(pid)
    related = Product.query.filter_by(category_id=product.category_id).filter(Product.id != pid).limit(4).all()
    reviews = Review.query.filter_by(product_id=pid).order_by(Review.created_at.desc()).all()
    in_wishlist = False
    user_review = None
    if 'user_id' in session:
        in_wishlist = Wishlist.query.filter_by(user_id=session['user_id'], product_id=pid).first() is not None
        user_review = Review.query.filter_by(product_id=pid, user_id=session['user_id']).first()
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter(Review.product_id == pid).scalar()
    rating_count = Review.query.filter_by(product_id=pid).count()
    return render_template('product_detail.html', product=product,
        related=related, reviews=reviews, in_wishlist=in_wishlist,
        user_review=user_review, avg_rating=avg_rating or 0, rating_count=rating_count)

@app.route('/product/<int:pid>/review', methods=['POST'])
@login_required
@csrf.exempt
def add_review(pid):
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment')
    Product.query.get_or_404(pid)
    existing = Review.query.filter_by(product_id=pid, user_id=session['user_id']).first()
    if existing:
        existing.rating = rating
        existing.comment = comment
        existing.is_approved = True
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Review updated!'})
        flash('Review updated!', 'success')
        return redirect(url_for('product_detail', pid=pid))
    if rating and comment:
        review = Review(product_id=pid, user_id=session['user_id'], rating=rating, comment=comment, is_approved=True)
        db.session.add(review)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Review posted!'})
        flash('Review posted!', 'success')
    return redirect(url_for('product_detail', pid=pid))

# ====== CART ======
@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<int:pid>', methods=['POST'])
@csrf.exempt
def add_to_cart(pid):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first', 'login_url': url_for('login')})
    product = Product.query.get_or_404(pid)
    qty = request.form.get('quantity', 1, type=int)
    if qty < 1: qty = 1
    existing = Cart.query.filter_by(user_id=session['user_id'], product_id=pid).first()
    if existing:
        existing.quantity += qty
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=pid, quantity=qty)
        db.session.add(cart_item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Added to cart!', 'cart_count': get_cart_count()})

@app.route('/cart/update/<int:cid>', methods=['POST'])
@login_required
@csrf.exempt
def update_cart(cid):
    item = Cart.query.get_or_404(cid)
    qty = request.form.get('quantity', type=int)
    if qty and qty > 0:
        item.quantity = qty
    else:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:cid>')
@login_required
def remove_from_cart(cid):
    item = Cart.query.get_or_404(cid)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('cart'))

# ====== WISHLIST ======
@app.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=session['user_id']).all()
    return render_template('wishlist.html', items=items)

@app.route('/wishlist/add/<int:pid>', methods=['POST'])
@csrf.exempt
def add_to_wishlist(pid):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first', 'login_url': url_for('login')})
    existing = Wishlist.query.filter_by(user_id=session['user_id'], product_id=pid).first()
    if not existing:
        w = Wishlist(user_id=session['user_id'], product_id=pid)
        db.session.add(w)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Added to wishlist!', 'wishlist_count': get_wishlist_count()})
    return jsonify({'success': True, 'message': 'Already in wishlist!', 'wishlist_count': get_wishlist_count()})

@app.route('/wishlist/remove/<int:wid>')
@login_required
def remove_wishlist(wid):
    item = Wishlist.query.get_or_404(wid)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('wishlist'))

# ====== CHECKOUT ======
@app.route('/coupon/validate', methods=['POST'])
@login_required
@csrf.exempt
def validate_coupon():
    data = request.get_json()
    code = data.get('code', '')
    subtotal = float(data.get('subtotal', 0))
    coupon = Coupon.query.filter_by(code=code.upper(), is_active=True).first()
    if not coupon:
        return jsonify({'valid': False, 'message': 'Invalid coupon code'})
    if coupon.expiry_date and coupon.expiry_date < datetime.utcnow():
        return jsonify({'valid': False, 'message': 'Coupon has expired'})
    if coupon.current_uses >= coupon.max_uses:
        return jsonify({'valid': False, 'message': 'Coupon usage limit reached'})
    uid = session['user_id']
    usage_count = CouponUsage.query.filter_by(coupon_id=coupon.id, user_id=uid).count()
    if usage_count >= coupon.max_uses_per_user:
        return jsonify({'valid': False, 'message': f'You can only use this coupon {coupon.max_uses_per_user} time(s)'})
    discount = round(subtotal * coupon.discount_percent / 100, 2)
    session['validated_coupon'] = code.upper()
    session.modified = True
    return jsonify({'valid': True, 'discount': discount, 'percent': coupon.discount_percent, 'message': f'Coupon applied! You save ${discount:.2f}'})

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def checkout():
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    if not cart_items:
        return redirect(url_for('cart'))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    tax = round(subtotal * 0.08, 2)
    shipping = 5.99 if subtotal < 50 else 0
    total = subtotal + tax + shipping

    if request.method == 'POST':
        shipping_addr = request.form.get('shipping_address')
        billing_addr = request.form.get('billing_address')
        shipping_method = request.form.get('shipping_method')
        payment_method = request.form.get('payment_method')
        coupon_code = request.form.get('coupon_code')

        discount = 0
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
            if not coupon:
                flash('Invalid coupon code', 'danger')
            elif coupon.expiry_date and coupon.expiry_date < datetime.utcnow():
                flash('Coupon has expired', 'danger')
            elif coupon.current_uses >= coupon.max_uses:
                flash('Coupon usage limit reached', 'danger')
            else:
                uid = session['user_id']
                usage_count = CouponUsage.query.filter_by(coupon_id=coupon.id, user_id=uid).count()
                if usage_count >= coupon.max_uses_per_user:
                    flash(f'You can only use this coupon {coupon.max_uses_per_user} time(s)', 'danger')
                else:
                    discount = round(subtotal * coupon.discount_percent / 100, 2)
                    coupon.current_uses += 1
                    usage = CouponUsage(coupon_id=coupon.id, user_id=session['user_id'])
                    db.session.add(usage)
                flash(f'Coupon applied! You saved ${discount:.2f}', 'success')

        order = Order(
            order_number=gen_order_number(),
            user_id=session['user_id'],
            status='Pending',
            total_amount=total - discount,
            shipping_address=shipping_addr,
            billing_address=billing_addr,
            shipping_method=shipping_method,
            payment_method=payment_method,
            coupon_code=coupon_code,
            discount_amount=discount,
            tax_amount=tax
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            oi = OrderItem(order_id=order.id, product_id=item.product_id,
                quantity=item.quantity, price=item.product.price)
            db.session.add(oi)
            product = Product.query.get(item.product_id)
            if product:
                product.stock -= item.quantity
            db.session.delete(item)

        db.session.commit()
        session.pop('validated_coupon', None)
        return redirect(url_for('payment', oid=order.id))

    validated_coupon = session.get('validated_coupon')
    discount = 0
    discount_percent = 0
    if validated_coupon:
        coupon = Coupon.query.filter_by(code=validated_coupon, is_active=True).first()
        uid = session['user_id']
        if coupon and not (coupon.expiry_date and coupon.expiry_date < datetime.utcnow()) and coupon.current_uses < coupon.max_uses:
            usage_count = CouponUsage.query.filter_by(coupon_id=coupon.id, user_id=uid).count()
            if usage_count < coupon.max_uses_per_user:
                discount_percent = coupon.discount_percent
                discount = round(subtotal * discount_percent / 100, 2)
    return render_template('checkout.html', cart_items=cart_items,
        subtotal=subtotal, tax=tax, shipping=shipping, total=total,
        validated_coupon=validated_coupon, discount=discount, discount_percent=discount_percent)

# ====== PAYMENT ======
@app.route('/payment/<int:oid>', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def payment(oid):
    order = Order.query.get_or_404(oid)
    if request.method == 'POST':
        method = request.form.get('payment_method')
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method=method,
            payment_status='Completed',
            transaction_id='TXN' + gen_order_number()
        )
        db.session.add(payment)
        order.payment_status = 'Completed'
        order.status = 'Processing'
        db.session.commit()
        return redirect(url_for('order_confirmation', oid=order.id))
    return render_template('payment.html', order=order)

# ====== ORDER CONFIRMATION ======
@app.route('/order-confirmation/<int:oid>')
@login_required
def order_confirmation(oid):
    order = Order.query.get_or_404(oid)
    return render_template('order_confirmation.html', order=order)

# ====== ORDER TRACKING ======
@app.route('/orders')
@login_required
def orders():
    orders_list = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders_list)

@app.route('/order/<int:oid>')
@login_required
def order_detail(oid):
    order = Order.query.get_or_404(oid)
    return render_template('order_detail.html', order=order)

@app.route('/order/<int:oid>/invoice')
@login_required
def order_invoice(oid):
    order = Order.query.get_or_404(oid)
    if order.user_id != session['user_id']:
        abort(403)
    from fpdf import FPDF
    import io
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()

    # Colors
    accent = (31, 41, 55)
    light_gray = (241, 245, 249)
    med_gray = (100, 116, 139)
    green = (16, 185, 129)

    # Header bar
    pdf.set_fill_color(*accent)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_xy(15, 10)
    pdf.cell(0, 12, 'Shafi\'s Shop')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_xy(15, 24)
    pdf.cell(0, 6, 'Your Trusted Online Store')
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_xy(15, 34)
    pdf.cell(0, 8, 'INVOICE')

    # Invoice details on right
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(120, 10)
    pdf.cell(80, 5, f'Order: {order.order_number}', align='R')
    pdf.set_xy(120, 16)
    pdf.cell(80, 5, f'Date: {order.created_at.strftime("%B %d, %Y")}', align='R')
    pdf.set_xy(120, 22)
    pdf.cell(80, 5, f'Status: {order.status}', align='R')
    if order.payment_method:
        pdf.set_xy(120, 28)
        pdf.cell(80, 5, f'Payment: {order.payment_method.replace("_", " ").title()}', align='R')

    # Bill To section
    pdf.set_text_color(*accent)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_xy(15, 58)
    pdf.cell(0, 6, 'BILL TO')
    pdf.set_draw_color(*accent)
    pdf.line(15, 65, 195, 65)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(15, 69)
    pdf.multi_cell(80, 5, order.billing_address or order.shipping_address or 'N/A')

    # Order info
    pdf.set_text_color(*accent)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_xy(110, 58)
    pdf.cell(0, 6, 'ORDER DETAILS')
    pdf.line(110, 65, 195, 65)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 9)
    info_y = 69
    subtotal_calc = sum(item.price * item.quantity for item in order.items)
    ship = 5.99 if subtotal_calc < 50 else 0
    pdf.set_xy(110, info_y); pdf.cell(40, 5, 'Subtotal:')
    pdf.set_xy(155, info_y); pdf.cell(35, 5, f'${subtotal_calc:.2f}', align='R')
    pdf.set_xy(110, info_y + 6); pdf.cell(40, 5, 'Shipping:')
    pdf.set_xy(155, info_y + 6); pdf.cell(35, 5, f'${ship:.2f}' if ship > 0 else 'Free', align='R')
    if order.tax_amount:
        pdf.set_xy(110, info_y + 12); pdf.cell(40, 5, 'Tax:')
        pdf.set_xy(155, info_y + 12); pdf.cell(35, 5, f'${order.tax_amount:.2f}', align='R')
    if order.discount_amount:
        pdf.set_text_color(*green)
        pdf.set_xy(110, info_y + 18 if not order.tax_amount else info_y + 18); pdf.cell(40, 5, 'Discount:')
        pdf.set_xy(155, info_y + 18 if not order.tax_amount else info_y + 18); pdf.cell(35, 5, f'-${order.discount_amount:.2f}', align='R')
        pdf.set_text_color(0, 0, 0)

    # Items table
    table_top = 105
    pdf.set_fill_color(*accent)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    col_w = [90, 20, 30, 30, 30]
    headers = ['Product', 'Qty', 'Price', 'Discount', 'Total']
    x_start = 15
    pdf.set_xy(x_start, table_top)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 8, h, border=0, fill=True, align='C')
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 9)
    y = table_top + 8
    for item in order.items:
        pdf.set_xy(x_start, y)
        pdf.cell(col_w[0], 7, (item.product.name[:40] if item.product else 'Product'), border=0)
        pdf.cell(col_w[1], 7, str(item.quantity), border=0, align='C')
        pdf.cell(col_w[2], 7, f'${item.price:.2f}', border=0, align='C')
        disc = 0
        pdf.cell(col_w[3], 7, f'${disc:.2f}', border=0, align='C')
        pdf.cell(col_w[4], 7, f'${item.price * item.quantity:.2f}', border=0, align='C')
        y += 7

    # Alternating row colors
    pdf.set_fill_color(*light_gray)
    for i, item in enumerate(order.items):
        if i % 2 == 0:
            pdf.rect(x_start, table_top + 8 + i * 7, sum(col_w), 7, 'F')
            # Re-draw text on top
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_xy(x_start, table_top + 8 + i * 7)
            pdf.cell(col_w[0], 7, (item.product.name[:40] if item.product else 'Product'), border=0)
            pdf.cell(col_w[1], 7, str(item.quantity), border=0, align='C')
            pdf.cell(col_w[2], 7, f'${item.price:.2f}', border=0, align='C')
            pdf.cell(col_w[3], 7, '$0.00', border=0, align='C')
            pdf.cell(col_w[4], 7, f'${item.price * item.quantity:.2f}', border=0, align='C')

    # Re-draw header on top of filled rows
    pdf.set_fill_color(*accent)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_xy(x_start, table_top)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 8, h, border=0, fill=True, align='C')

    # Total box
    total_y = y + 10
    pdf.set_draw_color(*accent)
    pdf.set_fill_color(*accent)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.rect(130, total_y, 65, 12, 'F')
    pdf.set_xy(130, total_y)
    pdf.cell(30, 12, '  TOTAL:', align='L')
    pdf.cell(35, 12, f'${order.total_amount:.2f}', align='R')

    # Footer
    pdf.set_text_color(*med_gray)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_xy(15, 270)
    pdf.cell(0, 5, 'Shafi\'s Shop | Thank you for your purchase!', align='C')
    pdf.set_xy(15, 276)
    pdf.cell(0, 5, 'If you have any questions, please contact our support team.', align='C')

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read(), 200, {'Content-Type': 'application/pdf', 'Content-Disposition': f'attachment; filename=invoice_{order.order_number}.pdf'}

# ====== COMPARE ======
@app.route('/compare')
def compare_products():
    ids = request.args.getlist('ids', type=int)
    products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    return render_template('compare.html', products=products)

# ====== STATIC PAGES ======
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        contact = Contact(name=name, email=email, subject=subject,
            message=message, ticket_number=gen_ticket())
        db.session.add(contact)
        db.session.commit()
        flash(f'Your ticket #{contact.ticket_number} has been created!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/returns')
def returns():
    return render_template('returns.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/blog')
def blog():
    posts = Blog.query.order_by(Blog.created_at.desc()).all()
    return render_template('blog.html', posts=posts)

@app.route('/blog/<int:bid>')
def blog_detail(bid):
    post = Blog.query.get_or_404(bid)
    comments = BlogComment.query.filter_by(blog_id=bid).order_by(BlogComment.created_at.desc()).all()
    avg_rating = db.session.query(db.func.avg(BlogRating.rating)).filter(BlogRating.blog_id == bid).scalar()
    rating_count = BlogRating.query.filter_by(blog_id=bid).count()
    user_rating = None
    user_comment = None
    if 'user_id' in session:
        user_rating = BlogRating.query.filter_by(blog_id=bid, user_id=session['user_id']).first()
        user_comment = BlogComment.query.filter_by(blog_id=bid, user_id=session['user_id']).first()
    return render_template('blog_detail.html', post=post, comments=comments,
        avg_rating=avg_rating or 0, rating_count=rating_count,
        user_rating=user_rating, user_comment=user_comment)

@app.route('/blog/<int:bid>/comment', methods=['POST'])
@login_required
@csrf.exempt
def add_blog_comment(bid):
    Blog.query.get_or_404(bid)
    comment = request.form.get('comment')
    if not comment:
        return jsonify({'success': False, 'message': 'Comment is required.'})
    existing = BlogComment.query.filter_by(blog_id=bid, user_id=session['user_id']).first()
    if existing:
        existing.comment = comment
        existing.is_approved = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Comment updated!'})
    c = BlogComment(blog_id=bid, user_id=session['user_id'], comment=comment, is_approved=True)
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Comment posted!'})

@app.route('/blog/<int:bid>/rate', methods=['POST'])
@login_required
@csrf.exempt
def add_blog_rating(bid):
    Blog.query.get_or_404(bid)
    rating = request.form.get('rating', type=int)
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Invalid rating.'})
    existing = BlogRating.query.filter_by(blog_id=bid, user_id=session['user_id']).first()
    if existing:
        existing.rating = rating
    else:
        r = BlogRating(blog_id=bid, user_id=session['user_id'], rating=rating)
        db.session.add(r)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Rating submitted!'})

# ====== ADMIN ======
@app.route('/admin')
@admin_required
def admin_dashboard():
    current_user = User.query.get(session['user_id'])
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()

    # Chart data: daily revenue (last 7 days)
    from datetime import timedelta
    today = datetime.utcnow().date()
    rev_labels = []
    rev_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        rev_labels.append(day.strftime('%a'))
        day_total = db.session.query(db.func.coalesce(db.func.sum(Order.total_amount), 0))\
            .filter(db.func.date(Order.created_at) == day).scalar()
        rev_data.append(float(day_total))

    # Chart data: order status counts
    statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    status_counts = []
    status_colors = ['#f59e0b', '#3b82f6', '#8b5cf6', '#10b981', '#ef4444']
    for s in statuses:
        status_counts.append(Order.query.filter_by(status=s).count())

    # Blog stats
    total_blog_posts = Blog.query.count()
    total_blog_comments = BlogComment.query.count()
    total_blog_ratings = BlogRating.query.count()
    return render_template('admin_dashboard.html',
        user=current_user, total_users=total_users, total_products=total_products,
        total_orders=total_orders, total_revenue=total_revenue,
        recent_orders=recent_orders, recent_users=recent_users,
        rev_labels=rev_labels, rev_data=rev_data,
        statuses=statuses, status_counts=status_counts, status_colors=status_colors,
        total_blog_posts=total_blog_posts, total_blog_comments=total_blog_comments,
        total_blog_ratings=total_blog_ratings)

@app.route('/admin/users')
@admin_required
def admin_users():
    current_user = User.query.get(session['user_id'])
    users = User.query.all()
    return render_template('admin_users.html', users=users, user=current_user)

@app.route('/admin/user/delete/<int:uid>')
@admin_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted', 'danger')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/add', methods=['POST'])
@admin_required
def admin_add_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('admin_users'))
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'danger')
        return redirect(url_for('admin_users'))
    profile_image = ''
    file = request.files.get('profile_image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"user_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        profile_image = url_for('static', filename=f'uploads/{filename}')
    elif request.form.get('profile_image'):
        profile_image = request.form['profile_image']
    role = request.form.get('role', 'User')
    user = User(
        username=username, email=email, password=generate_password_hash(password),
        is_admin=(role == 'Admin'),
        role=role,
        full_name=request.form.get('full_name', ''),
        phone=request.form.get('phone', ''),
        address=request.form.get('address', ''),
        profile_image=profile_image
    )
    db.session.add(user)
    db.session.commit()
    flash(f'User {username} created!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/edit/<int:uid>', methods=['POST'])
@admin_required
def admin_edit_user(uid):
    user = User.query.get_or_404(uid)
    user.username = request.form['username']
    user.email = request.form['email']
    user.full_name = request.form.get('full_name', '')
    user.phone = request.form.get('phone', '')
    user.address = request.form.get('address', '')
    role = request.form.get('role', 'User')
    user.role = role
    user.is_admin = (role == 'Admin')
    file = request.files.get('profile_image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"user_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_image = url_for('static', filename=f'uploads/{filename}')
    elif request.form.get('profile_image'):
        user.profile_image = request.form['profile_image']
    if request.form.get('password'):
        user.password = generate_password_hash(request.form['password'])
    db.session.commit()
    flash(f'User {user.username} updated!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    current_user = User.query.get(session['user_id'])
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', '')
        current_user.email = request.form.get('email', '')
        current_user.phone = request.form.get('phone', '')
        current_user.address = request.form.get('address', '')
        file = request.files.get('profile_image_file')
        if file and file.filename and allowed_file(file.filename):
            filename = f"user_{random.randint(10000,99999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_image = url_for('static', filename=f'uploads/{filename}')
        elif request.form.get('profile_image'):
            current_user.profile_image = request.form['profile_image']
        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form['password'])
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('admin_profile'))
    return render_template('admin_profile.html', user=current_user)

# ----- Admin Products -----
@app.route('/admin/products')
@admin_required
def admin_products():
    current_user = User.query.get(session['user_id'])
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    subcategories = SubCategory.query.all()
    return render_template('admin_products.html', products=products, categories=categories, subcategories=subcategories, user=current_user)

@app.route('/admin/product/add', methods=['POST'])
@admin_required
def admin_add_product():
    cat_id = request.form.get('category_id')
    image_url = request.form.get('image', '')
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"product_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = url_for('static', filename=f'uploads/{filename}')
    elif image_url:
        image = image_url
    else:
        image = 'https://placehold.co/300x300/f5f5f5/333?text=Product'
    subcat_id = request.form.get('subcategory_id')
    product = Product(
        name=request.form['name'],
        description=request.form.get('description', ''),
        price=float(request.form['price']),
        old_price=float(request.form['old_price']) if request.form.get('old_price') else None,
        stock=int(request.form.get('stock', 0)),
        category_id=int(cat_id) if cat_id else 1,
        subcategory_id=int(subcat_id) if subcat_id else None,
        brand=request.form.get('brand', ''),
        discount=int(request.form.get('discount', 0) or 0),
        is_featured=bool(request.form.get('is_featured')),
        is_new=bool(request.form.get('is_new')),
        is_best=bool(request.form.get('is_best')),
        specifications=request.form.get('specifications', ''),
        image=image
    )
    db.session.add(product)
    db.session.commit()
    flash('Product added!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/edit/<int:pid>', methods=['POST'])
@admin_required
def admin_edit_product(pid):
    product = Product.query.get_or_404(pid)
    product.name = request.form['name']
    product.description = request.form.get('description', '')
    product.price = float(request.form['price'])
    product.old_price = float(request.form['old_price']) if request.form.get('old_price') else None
    product.stock = int(request.form.get('stock', 0))
    cat_id = request.form.get('category_id')
    product.category_id = int(cat_id) if cat_id else product.category_id
    subcat_id = request.form.get('subcategory_id')
    product.subcategory_id = int(subcat_id) if subcat_id else None
    product.brand = request.form.get('brand', '')
    product.discount = int(request.form.get('discount', 0) or 0)
    product.is_featured = bool(request.form.get('is_featured'))
    product.is_new = bool(request.form.get('is_new'))
    product.is_best = bool(request.form.get('is_best'))
    product.specifications = request.form.get('specifications', '')
    image_url = request.form.get('image', '')
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"product_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product.image = url_for('static', filename=f'uploads/{filename}')
    elif image_url:
        product.image = image_url
    db.session.commit()
    flash('Product updated!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/delete/<int:pid>')
@admin_required
def admin_delete_product(pid):
    product = Product.query.get_or_404(pid)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted!', 'danger')
    return redirect(url_for('admin_products'))

# ----- Admin Categories -----
@app.route('/admin/categories')
@admin_required
def admin_categories():
    current_user = User.query.get(session['user_id'])
    categories = Category.query.all()
    return render_template('admin_categories.html', categories=categories, user=current_user)

@app.route('/admin/category/add', methods=['POST'])
@admin_required
def admin_add_category():
    image = ''
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"cat_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = url_for('static', filename=f'uploads/{filename}')
    elif request.form.get('image'):
        image = request.form['image']
    cat = Category(name=request.form['name'], description=request.form.get('description', ''), image=image)
    db.session.add(cat)
    db.session.commit()
    flash('Category added!', 'success')
    return redirect(url_for('admin_categories'))

# ----- Admin SubCategories -----
@app.route('/admin/subcategories')
@admin_required
def admin_subcategories():
    current_user = User.query.get(session['user_id'])
    categories = Category.query.all()
    return render_template('admin_subcategories.html', categories=categories, user=current_user)

@app.route('/admin/subcategory/add', methods=['POST'])
@admin_required
def admin_add_subcategory():
    sub = SubCategory(name=request.form['name'], category_id=request.form['category_id'])
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"sub_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        sub.image = url_for('static', filename=f'uploads/{filename}')
    db.session.add(sub)
    db.session.commit()
    flash('Subcategory added!', 'success')
    return redirect(url_for('admin_subcategories'))

@app.route('/admin/subcategory/edit/<int:sid>', methods=['POST'])
@admin_required
def admin_edit_subcategory(sid):
    sub = SubCategory.query.get_or_404(sid)
    sub.name = request.form['name']
    sub.category_id = request.form['category_id']
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"sub_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        sub.image = url_for('static', filename=f'uploads/{filename}')
    db.session.commit()
    flash('Subcategory updated!', 'success')
    return redirect(url_for('admin_subcategories'))

@app.route('/admin/subcategory/delete/<int:sid>')
@admin_required
def admin_delete_subcategory(sid):
    sub = SubCategory.query.get_or_404(sid)
    db.session.delete(sub)
    db.session.commit()
    flash('Subcategory deleted!', 'danger')
    return redirect(url_for('admin_subcategories'))

@app.route('/admin/subcategories/seed-from-file')
@admin_required
def seed_subcategories():
    import re
    txt_path = os.path.join(BASE_DIR, 'categories.txt')
    if not os.path.exists(txt_path):
        flash('categories.txt not found!', 'danger')
        return redirect(url_for('admin_subcategories'))
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    current_cat = None
    cat_count = 0
    sub_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'🔹\s*\d+\.\s*(.+)', line)
        if m:
            cat_name = m.group(1).strip()
            current_cat = Category.query.filter_by(name=cat_name).first()
            if not current_cat:
                current_cat = Category(name=cat_name, description='', image='/static/img/no-image.png')
                db.session.add(current_cat)
                db.session.flush()
                cat_count += 1
            continue
        if current_cat and line and not line.startswith('🔹'):
            existing = SubCategory.query.filter_by(name=line, category_id=current_cat.id).first()
            if not existing:
                sub = SubCategory(name=line, category_id=current_cat.id)
                slug = re.sub(r'[^a-z0-9]+', '-', line.lower()).strip('-')[:50]
                sub.image = f'https://picsum.photos/seed/{slug}/200/200'
                db.session.add(sub)
                sub_count += 1
    db.session.commit()
    flash(f'{cat_count} categories + {sub_count} subcategories imported from categories.txt with images!', 'success')
    return redirect(url_for('admin_subcategories'))

@app.route('/admin/category/edit/<int:cid>', methods=['POST'])
@admin_required
def admin_edit_category(cid):
    cat = Category.query.get_or_404(cid)
    cat.name = request.form['name']
    cat.description = request.form.get('description', '')
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = f"cat_{random.randint(10000,99999)}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cat.image = url_for('static', filename=f'uploads/{filename}')
    elif request.form.get('image'):
        cat.image = request.form['image']
    db.session.commit()
    flash('Category updated!', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/category/delete/<int:cid>')
@admin_required
def admin_delete_category(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted!', 'danger')
    return redirect(url_for('admin_categories'))

# ----- Admin Orders -----
@app.route('/admin/orders')
@admin_required
def admin_orders():
    current_user = User.query.get(session['user_id'])
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders, user=current_user)

@app.route('/admin/order/update-status/<int:oid>', methods=['POST'])
@admin_required
def admin_update_order_status(oid):
    order = Order.query.get_or_404(oid)
    order.status = request.form['status']
    db.session.commit()
    flash('Order status updated!', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/order/<int:oid>')
@admin_required
def admin_order_detail(oid):
    current_user = User.query.get(session['user_id'])
    order = Order.query.get_or_404(oid)
    return render_template('admin_order_detail.html', order=order, user=current_user)

# ----- Admin Customers -----
@app.route('/admin/customers')
@admin_required
def admin_customers():
    current_user = User.query.get(session['user_id'])
    customers = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_customers.html', customers=customers, user=current_user)

# ----- Admin Inventory -----
@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    current_user = User.query.get(session['user_id'])
    products = Product.query.order_by(Product.stock.asc()).all()
    return render_template('admin_inventory.html', products=products, user=current_user)

@app.route('/admin/inventory/update/<int:pid>', methods=['POST'])
@admin_required
def admin_inventory_update(pid):
    product = Product.query.get_or_404(pid)
    stock = request.form.get('stock', type=int)
    if stock is not None and stock >= 0:
        product.stock = stock
        db.session.commit()
        flash(f'Stock updated for {product.name}', 'success')
    return redirect(url_for('admin_inventory'))

# ----- Admin Coupons -----
@app.route('/admin/coupons')
@admin_required
def admin_coupons():
    current_user = User.query.get(session['user_id'])
    coupons = Coupon.query.all()
    return render_template('admin_coupons.html', coupons=coupons, user=current_user, now=datetime.utcnow())

@app.route('/admin/coupon/add', methods=['POST'])
@admin_required
def admin_add_coupon():
    max_uses = request.form.get('max_uses')
    max_per_user = request.form.get('max_uses_per_user')
    coupon = Coupon(
        code=request.form['code'].upper(),
        discount_percent=int(request.form['discount_percent']),
        max_uses=int(max_uses) if max_uses else 100,
        max_uses_per_user=int(max_per_user) if max_per_user else 1,
        expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d') if request.form.get('expiry_date') else None
    )
    db.session.add(coupon)
    db.session.commit()
    flash('Coupon added!', 'success')
    return redirect(url_for('admin_coupons'))

@app.route('/admin/coupon/edit/<int:cid>', methods=['POST'])
@admin_required
def admin_edit_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    max_uses = request.form.get('max_uses')
    max_per_user = request.form.get('max_uses_per_user')
    c.code = request.form['code'].upper()
    c.discount_percent = int(request.form['discount_percent'])
    c.max_uses = int(max_uses) if max_uses else 100
    c.max_uses_per_user = int(max_per_user) if max_per_user else 1
    c.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d') if request.form.get('expiry_date') else None
    db.session.commit()
    flash('Coupon updated!', 'success')
    return redirect(url_for('admin_coupons'))

@app.route('/admin/coupon/delete/<int:cid>')
@admin_required
def admin_delete_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Coupon deleted!', 'danger')
    return redirect(url_for('admin_coupons'))

# ----- Admin Reports -----
@app.route('/admin/reports')
@admin_required
def admin_reports():
    current_user = User.query.get(session['user_id'])
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_orders = Order.query.count()
    total_products = Product.query.count()
    total_customers = User.query.count()
    orders_by_status = db.session.query(Order.status, db.func.count(Order.id)).group_by(Order.status).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    return render_template('admin_reports.html',
        user=current_user, total_revenue=total_revenue, total_orders=total_orders,
        total_products=total_products, total_customers=total_customers,
        orders_by_status=orders_by_status, recent_orders=recent_orders)

# ----- Admin Reviews -----
@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    current_user = User.query.get(session['user_id'])
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin_reviews.html', reviews=reviews, user=current_user)

@app.route('/admin/review/approve/<int:rid>')
@admin_required
def admin_approve_review(rid):
    r = Review.query.get_or_404(rid)
    r.is_approved = True
    db.session.commit()
    flash('Review approved!', 'success')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/review/disapprove/<int:rid>')
@admin_required
def admin_disapprove_review(rid):
    r = Review.query.get_or_404(rid)
    r.is_approved = False
    db.session.commit()
    flash('Review disapproved!', 'warning')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/review/delete/<int:rid>')
@admin_required
def admin_delete_review(rid):
    r = Review.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash('Review deleted!', 'danger')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/review/edit/<int:rid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_review(rid):
    r = Review.query.get_or_404(rid)
    if request.method == 'POST':
        r.rating = request.form.get('rating', type=int)
        r.comment = request.form.get('comment')
        r.is_approved = bool(request.form.get('is_approved'))
        db.session.commit()
        flash('Review updated!', 'success')
        return redirect(url_for('admin_reviews'))
    return render_template('admin_review_edit.html', review=r)

# ----- Admin Contacts -----
@app.route('/admin/contacts')
@admin_required
def admin_contacts():
    current_user = User.query.get(session['user_id'])
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    return render_template('admin_contacts.html', contacts=contacts, user=current_user)

@app.route('/admin/contact/close/<int:cid>')
@admin_required
def admin_close_contact(cid):
    c = Contact.query.get_or_404(cid)
    c.status = 'Closed' if c.status == 'Open' else 'Open'
    db.session.commit()
    flash(f'Ticket {c.ticket_number} status updated!', 'success')
    return redirect(url_for('admin_contacts'))

@app.route('/admin/contact/delete/<int:cid>')
@admin_required
def admin_delete_contact(cid):
    c = Contact.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Contact ticket deleted!', 'danger')
    return redirect(url_for('admin_contacts'))

# ----- Admin Blog -----
@app.route('/admin/blog')
@admin_required
def admin_blog():
    current_user = User.query.get(session['user_id'])
    posts = Blog.query.order_by(Blog.created_at.desc()).all()
    return render_template('admin_blog.html', posts=posts, user=current_user)

@app.route('/admin/blog/add', methods=['GET', 'POST'])
@admin_required
def admin_add_blog():
    current_user = User.query.get(session['user_id'])
    if request.method == 'POST':
        image_url = request.form.get('image', '')
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            filename = f"blog_{random.randint(10000,99999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = url_for('static', filename=f'uploads/{filename}')
        elif image_url:
            image = image_url
        else:
            image = ''
        post = Blog(
            title=request.form['title'],
            content=request.form['content'],
            author=request.form.get('author', 'Admin'),
            image=image,
            created_at=datetime.utcnow()
        )
        db.session.add(post)
        db.session.commit()
        flash('Blog post created!', 'success')
        return redirect(url_for('admin_blog'))
    return render_template('admin_blog_add.html', user=current_user)

@app.route('/admin/blog/edit/<int:bid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog(bid):
    current_user = User.query.get(session['user_id'])
    post = Blog.query.get_or_404(bid)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.author = request.form.get('author', post.author)
        image_url = request.form.get('image', '')
        file = request.files.get('image_file')
        if file and file.filename and allowed_file(file.filename):
            filename = f"blog_{random.randint(10000,99999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            post.image = url_for('static', filename=f'uploads/{filename}')
        elif image_url:
            post.image = image_url
        db.session.commit()
        flash('Blog post updated!', 'success')
        return redirect(url_for('admin_blog'))
    return render_template('admin_blog_edit.html', post=post, user=current_user)

@app.route('/admin/blog/delete/<int:bid>')
@admin_required
def admin_delete_blog(bid):
    post = Blog.query.get_or_404(bid)
    BlogComment.query.filter_by(blog_id=bid).delete()
    BlogRating.query.filter_by(blog_id=bid).delete()
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted!', 'danger')
    return redirect(url_for('admin_blog'))

@app.route('/admin/blog/comments')
@admin_required
def admin_blog_comments():
    current_user = User.query.get(session['user_id'])
    comments = BlogComment.query.order_by(BlogComment.created_at.desc()).all()
    return render_template('admin_blog_comments.html', comments=comments, user=current_user)

@app.route('/admin/blog/comment/approve/<int:cid>')
@admin_required
def admin_approve_blog_comment(cid):
    c = BlogComment.query.get_or_404(cid)
    c.is_approved = True
    db.session.commit()
    flash('Comment approved!', 'success')
    return redirect(url_for('admin_blog_comments'))

@app.route('/admin/blog/comment/disapprove/<int:cid>')
@admin_required
def admin_disapprove_blog_comment(cid):
    c = BlogComment.query.get_or_404(cid)
    c.is_approved = False
    db.session.commit()
    flash('Comment disapproved!', 'warning')
    return redirect(url_for('admin_blog_comments'))

@app.route('/admin/blog/comment/edit/<int:cid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_blog_comment(cid):
    c = BlogComment.query.get_or_404(cid)
    if request.method == 'POST':
        c.comment = request.form['comment']
        c.is_approved = bool(request.form.get('is_approved'))
        db.session.commit()
        flash('Comment updated!', 'success')
        return redirect(url_for('admin_blog_comments'))
    return render_template('admin_blog_comment_edit.html', comment=c)

@app.route('/admin/blog/comment/delete/<int:cid>')
@admin_required
def admin_delete_blog_comment(cid):
    c = BlogComment.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Comment deleted!', 'danger')
    return redirect(url_for('admin_blog_comments'))

@app.route('/admin/blog/ratings')
@admin_required
def admin_blog_ratings():
    current_user = User.query.get(session['user_id'])
    ratings = BlogRating.query.order_by(BlogRating.id.desc()).all()
    return render_template('admin_blog_ratings.html', ratings=ratings, user=current_user)

@app.route('/admin/blog/rating/delete/<int:rid>')
@admin_required
def admin_delete_blog_rating(rid):
    r = BlogRating.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash('Rating deleted!', 'danger')
    return redirect(url_for('admin_blog_ratings'))

# ====== SEED DATA ======
def seed_data():
    if Category.query.count() > 0:
        return
    cats = ['Electronics', 'Fashion', 'Home & Kitchen', 'Beauty', 'Sports', 'Accessories']
    cat_images = {
        'Electronics': 'uploads/cat_electronics.jpg',
        'Fashion': 'uploads/cat_fashion.jpg',
        'Home & Kitchen': 'uploads/cat_home_and_kitchen.jpg',
        'Beauty': 'uploads/cat_beauty.jpg',
        'Sports': 'uploads/cat_sports.jpg',
        'Accessories': 'uploads/cat_accessories.jpg',
    }
    for c in cats:
        img = '/static/' + cat_images.get(c, '') if c in cat_images else ''
        db.session.add(Category(name=c, image=img))
    db.session.commit()

    products_data = [
        ('Wireless Headphones Pro', 'Premium wireless headphones', 59.99, 99.99, 50, 1, True, False, True, 40, 'AudioTech', 'Electronics'),
        ('Smart Watch Series 5', 'Advanced smartwatch', 139.99, 199.99, 30, 2, True, False, True, 30, 'WearTech', 'Fashion'),
        ('Running Sneakers Elite', 'Comfortable running shoes', 89.99, 119.99, 40, 2, False, True, False, 25, 'SportMax', 'Fashion'),
        ('Travel Backpack 45L', 'Spacious travel backpack', 34.99, 69.99, 60, 6, False, True, True, 50, 'TravelPro', 'Accessories'),
        ('UltraBook Pro 15"', 'High performance laptop', 999.99, 1299.99, 15, 1, True, False, True, 23, 'TechPro', 'Electronics'),
        ('Smartphone X Pro Max', 'Flagship smartphone', 799.99, 1099.99, 25, 1, True, False, True, 27, 'PhoneMax', 'Electronics'),
        ('DSLR Camera 4K', 'Professional camera', 549.99, 749.99, 20, 1, True, False, False, 27, 'CamPro', 'Electronics'),
        ('iPad Air 12.9"', 'Apple iPad Air', 699.99, 899.99, 18, 1, True, False, True, 22, 'Apple', 'Electronics'),
        ('Leather Biker Jacket', 'Premium leather jacket', 149.99, None, 25, 2, False, True, False, 0, 'FashionPro', 'Fashion'),
        ('Bluetooth Speaker Boom', 'Portable Bluetooth speaker', 79.99, 99.99, 35, 1, False, True, False, 20, 'AudioTech', 'Electronics'),
        ('Premium Perfume Collection', 'Luxury perfume', 89.99, None, 40, 4, False, True, False, 0, 'Luxe', 'Beauty'),
        ('Premium Yoga Mat', 'Non-slip yoga mat', 39.99, 49.99, 55, 5, False, True, False, 20, 'FitPro', 'Sports'),
        ('4K Ultra HD Monitor 27"', 'High resolution monitor', 349.99, 449.99, 12, 1, False, False, True, 22, 'TechPro', 'Electronics'),
        ('Gaming Headset RGB', 'RGB gaming headset', 59.99, 89.99, 45, 1, False, False, True, 33, 'GameAudio', 'Electronics'),
        ('Classic Leather Watch', 'Elegant leather watch', 199.99, 279.99, 22, 2, False, False, True, 29, 'TimePro', 'Fashion'),
        ('Casual Sneakers White', 'White casual sneakers', 69.99, 89.99, 38, 2, False, False, True, 22, 'SportMax', 'Fashion'),
    ]

    for p in products_data:
        cat = Category.query.filter_by(name=p[11]).first()
        product = Product(
            name=p[0], description=p[1], price=p[2], old_price=p[3],
            stock=p[4], category_id=cat.id, is_featured=p[6],
            is_new=p[7], is_best=p[8], discount=p[9], brand=p[10],
            image=f'https://placehold.co/300x300/f5f5f5/333?text={p[0].replace(" ", "+")}'
        )
        db.session.add(product)
    db.session.commit()

    # Sample coupons
    coupons_data = [('SAVE10', 10, 50), ('SAVE20', 20, 30), ('WELCOME15', 15, 100)]
    for code, disc, uses in coupons_data:
        db.session.add(Coupon(code=code, discount_percent=disc,
            max_uses=uses, expiry_date=datetime.utcnow() + timedelta(days=30)))
    db.session.commit()

    # Sample blog posts
    posts = [
        ('Summer Fashion Trends 2025', 'Discover the hottest fashion trends this summer...', 'Admin'),
        ('Top 10 Gadgets of 2025', 'Check out our list of must-have gadgets...', 'Admin'),
        ('How to Choose the Perfect Sneakers', 'A complete guide to finding your ideal sneakers...', 'Admin'),
    ]
    for title, content, author in posts:
        db.session.add(Blog(title=title, content=content, author=author))
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@admin.com',
                password=generate_password_hash('admin123'), is_admin=True, role='Admin')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
