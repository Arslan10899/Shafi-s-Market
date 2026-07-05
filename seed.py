"""
Seed script: creates admin user, sample categories & products.
Run: python seed.py
"""
import bcrypt as _bcrypt
from slugify import slugify

from database import init_db, SessionLocal
from models import User, Category, Product, HeroSlide, SocialLink, Platform


def seed():
    init_db()
    db = SessionLocal()

    try:
        if db.query(User).first():
            print("Data already seeded.")
            return

        admin = User(
            username="admin",
            email="admin@azmart.com",
            password_hash=_bcrypt.hashpw("admin123".encode(), _bcrypt.gensalt()).decode(),
            full_name="Admin",
            role="admin",
        )
        db.add(admin)

        categories = [
            ("Electronics", "Latest gadgets and electronics", "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400"),
            ("Fashion", "Trendy clothing and accessories", "https://images.unsplash.com/photo-1445205170230-053b83016050?w=400"),
            ("Home & Kitchen", "Everything for your home", "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400"),
            ("Beauty & Health", "Skincare, makeup and wellness", "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400"),
            ("Sports & Outdoors", "Sports equipment and outdoor gear", "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400"),
            ("Toys & Games", "Fun for all ages", "https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=400"),
        ]

        cats = []
        for name, desc, img in categories:
            cat = Category(name=name, slug=slugify(name)[:120], description=desc, image=img)
            db.add(cat)
            cats.append(cat)
        db.flush()

        products = [
            ("Wireless Noise-Cancelling Headphones", "Premium ANC headphones with 30hr battery", 79.99, 149.99, 4.5, 0, "amazon", "https://www.amazon.com/dp/example01", True, True),
            ("Smart Watch Pro Series", "Fitness tracker with AMOLED display", 129.99, 199.99, 4.3, 0, "aliexpress", "https://www.aliexpress.com/item/example01", True, True),
            ("Portable Bluetooth Speaker", "Waterproof speaker with 360 sound", 49.99, 79.99, 4.2, 0, "amazon", "https://www.amazon.com/dp/example02", True, False),
            ("4K Action Camera", "Ultra HD action cam with stabilization", 89.99, 139.99, 4.4, 0, "daraz", "https://www.daraz.pk/products/example01", False, True),
            ("Men's Leather Jacket", "Genuine leather biker jacket", 89.99, 159.99, 4.6, 1, "amazon", "https://www.amazon.com/dp/example03", True, False),
            ("Women's Running Shoes", "Lightweight breathable mesh sneakers", 59.99, 99.99, 4.3, 1, "aliexpress", "https://www.aliexpress.com/item/example02", False, True),
            ("Designer Sunglasses", "UV400 protection polarized", 29.99, 59.99, 4.1, 1, "daraz", "https://www.daraz.pk/products/example02", False, False),
            ("Casual Cotton T-Shirt Pack", "3-pack premium quality cotton tees", 24.99, 44.99, 4.0, 1, "alibaba", "https://www.alibaba.com/product/example01", False, True),
            ("Non-Stick Cookware Set", "10-piece kitchen set with induction base", 69.99, 129.99, 4.5, 2, "amazon", "https://www.amazon.com/dp/example04", True, False),
            ("Robot Vacuum Cleaner", "Smart mapping, app controlled", 199.99, 349.99, 4.4, 2, "aliexpress", "https://www.aliexpress.com/item/example03", True, True),
            ("Stainless Steel Water Bottle", "Double wall vacuum insulated", 19.99, 34.99, 4.3, 2, "amazon", "https://www.amazon.com/dp/example05", False, False),
            ("LED Desk Lamp", "Touch control, 5 brightness levels", 34.99, 54.99, 4.2, 2, "daraz", "https://www.daraz.pk/products/example03", False, True),
            ("Vitamin C Serum", "Anti-aging with hyaluronic acid", 22.99, 39.99, 4.4, 3, "amazon", "https://www.amazon.com/dp/example06", True, False),
            ("Hair Dryer Professional", "Ionic 1875W with diffuser", 39.99, 69.99, 4.3, 3, "aliexpress", "https://www.aliexpress.com/item/example04", False, True),
            ("Organic Face Moisturizer", "Natural ingredients for glowing skin", 18.99, 29.99, 4.1, 3, "daraz", "https://www.daraz.pk/products/example04", False, False),
            ("Electric Toothbrush", "Sonic technology with 5 modes", 44.99, 79.99, 4.5, 3, "alibaba", "https://www.alibaba.com/product/example02", False, True),
            ("Yoga Mat Premium", "Non-slip, extra thick 6mm", 34.99, 54.99, 4.3, 4, "amazon", "https://www.amazon.com/dp/example07", True, False),
            ("Adjustable Dumbbell Set", "Space-saving 2-in-1 design", 149.99, 249.99, 4.6, 4, "aliexpress", "https://www.aliexpress.com/item/example05", False, True),
            ("Camping Tent 4-Person", "Waterproof, easy setup", 89.99, 159.99, 4.2, 4, "amazon", "https://www.amazon.com/dp/example08", False, False),
            ("Resistance Bands Set", "5 levels of resistance, portable", 19.99, 34.99, 4.1, 4, "daraz", "https://www.daraz.pk/products/example05", False, True),
            ("Remote Control Car", "4WD off-road RC truck", 44.99, 74.99, 4.3, 5, "amazon", "https://www.amazon.com/dp/example09", False, True),
            ("Board Game Collection", "5 classic family board games", 34.99, 54.99, 4.4, 5, "aliexpress", "https://www.aliexpress.com/item/example06", False, False),
            ("Building Blocks 1000pc", "Creative building kit for kids", 29.99, 49.99, 4.2, 5, "daraz", "https://www.daraz.pk/products/example06", False, True),
            ("Drone with Camera", "1080P HD, foldable, 30min flight", 99.99, 179.99, 4.0, 5, "alibaba", "https://www.alibaba.com/product/example03", False, False),
        ]

        unsplash_ids = [
            "1505740420928-5e560c06d30e", "1523275335684-37898b6baf30", "1542291026-2a717c0b1a2b",
            "1572635196237-14b3f281503f", "1526170375885-61d31f4b9b0e", "1491553895911-0055eca6402d",
            "1526947427132-0152a83d5d9a", "1503602642458-232111d65752", "1546868871-af0c74e6c4e7",
            "1560343090-f0409e92791a", "1585386953200-5c8b0e0e6f1d", "1596462502278-27bfdc403348",
            "1571019613454-1cb2f99b2d8b", "1526947427132-0152a83d5d9a", "1503602642458-232111d65752",
            "1491553895911-0055eca6402d", "1546868871-af0c74e6c4e7", "1560343090-f0409e92791a",
            "1526947427132-0152a83d5d9a", "1503602642458-232111d65752", "1491553895911-0055eca6402d",
            "1546868871-af0c74e6c4e7", "1560343090-f0409e92791a", "1526947427132-0152a83d5d9a",
        ]

        for i, p in enumerate(products):
            title, desc, price, old_price, rating, cat_idx, platform, url, featured, new = p
            prod = Product(
                title=title,
                slug=f"{slugify(title)[:200]}-{i+1}",
                short_description=desc,
                description=desc + ". Shop now at the best price with fast shipping. Limited stock available!",
                image=f"https://images.unsplash.com/photo-{unsplash_ids[i]}?w=400&h=400&fit=crop",
                price=price,
                old_price=old_price,
                currency="USD",
                is_active=True,
                rating=rating,
                category_id=cats[cat_idx].id,
                affiliate_platform=platform,
                affiliate_url=url,
                is_featured=featured,
                is_new=new,
            )
            db.add(prod)

        if not db.query(Platform).first():
            platforms = [
                ("Amazon", "fab fa-amazon", "https://www.amazon.com"),
                ("Daraz", "fas fa-shopping-bag", "https://www.daraz.pk"),
                ("AliExpress", "fas fa-globe", "https://www.aliexpress.com"),
                ("Alibaba", "fas fa-building", "https://www.alibaba.com"),
                ("eBay", "fab fa-ebay", "https://www.ebay.com"),
            ]
            for name, icon, url in platforms:
                db.add(Platform(name=name, icon=icon, base_url=url, is_active=True))
            db.commit()
            print("Platforms seeded!")

        if not db.query(SocialLink).first():
            socials = [
                ("Facebook", "https://facebook.com/safimarket", "fab fa-facebook", 1),
                ("Instagram", "https://instagram.com/safimarket", "fab fa-instagram", 2),
                ("Twitter", "https://twitter.com/safimarket", "fab fa-twitter", 3),
                ("YouTube", "https://youtube.com/@safimarket", "fab fa-youtube", 4),
            ]
            for platform, url, icon, order in socials:
                db.add(SocialLink(platform=platform, url=url, icon=icon, sort_order=order, is_active=True))
            db.commit()
            print("Social links seeded!")

        if not db.query(HeroSlide).first():
            hero_slides = [
                ("Shop the Best Deals", "Curated products from Amazon, Alibaba, AliExpress & Daraz — all in one place.", "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1600&q=80", "Start Shopping", "/shop", "primary", 1),
                ("Top Brands, Best Prices", "Discover thousands of products at unbeatable prices from top global brands.", "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1600&q=80", "View Best Deals", "/shop?sort=price_asc", "primary", 2),
                ("New Arrivals Every Day", "Stay ahead with the latest trends and newest products from around the world.", "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1600&q=80", "Explore New Arrivals", "/shop?sort=newest", "primary", 3),
                ("Shop by Category", "Find exactly what you need — Electronics, Fashion, Home & more from trusted sellers.", "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1600&q=80", "Browse Categories", "/shop", "outline", 4),
            ]
            for title, subtitle, img, btn_text, btn_url, btn_type, order in hero_slides:
                db.add(HeroSlide(title=title, subtitle=subtitle, image_url=img, btn_text=btn_text, btn_url=btn_url, btn_type=btn_type, sort_order=order, is_active=True))
            db.commit()
            print("Hero slides seeded!")

        db.commit()
        print("Database seeded successfully!")
        print("Admin login: username=admin, password=admin123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
