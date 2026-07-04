import os
os.environ['SECRET_KEY'] = 'update'
from database import SessionLocal
from models import Category

# Better quality images for each category (PNG-style cutout/product images)
new_images = {
    'beauty': 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=300&h=300&fit=crop&q=90',
    'electronics': 'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=300&h=300&fit=crop&q=90',
    'fashion': 'https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?w=300&h=300&fit=crop&q=90',
    'home-kitchen': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=300&h=300&fit=crop&q=90',
    'sports': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=300&h=300&fit=crop&q=90',
    'health-fitness': 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=300&h=300&fit=crop&q=90',
    'toys-games': 'https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=300&h=300&fit=crop&q=90',
    'automotive': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=300&h=300&fit=crop&q=90',
    'books': 'https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=300&h=300&fit=crop&q=90',
    'jewelry': 'https://images.unsplash.com/photo-1515562141589-87e3d4e2dd2a?w=300&h=300&fit=crop&q=90',
    'baby-products': 'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=300&h=300&fit=crop&q=90',
    'pet-supplies': 'https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=300&h=300&fit=crop&q=90',
    'groceries': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&h=300&fit=crop&q=90',
    'office-supplies': 'https://images.unsplash.com/photo-1499952127939-9bbf5af6c51c?w=300&h=300&fit=crop&q=90',
    'music': 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=300&h=300&fit=crop&q=90',
    'garden-outdoor': 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=300&h=300&fit=crop&q=90',
    'shoes': 'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=300&h=300&fit=crop&q=90',
    'watches': 'https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=300&h=300&fit=crop&q=90',
    'bags-luggage': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300&h=300&fit=crop&q=90',
    'computer-accessories': 'https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?w=300&h=300&fit=crop&q=90',
}

db = SessionLocal()
updated = 0
for slug, img in new_images.items():
    cat = db.query(Category).filter_by(slug=slug).first()
    if cat:
        cat.image = img
        updated += 1
db.commit()
db.close()
print(f'Updated {updated} category images')
