from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(1000), unique=True, nullable=False)
    published = db.Column(db.String(100))
    summary = db.Column(db.Text)
    image_url = db.Column(db.String(1000))
    source = db.Column(db.String(300))
    category = db.Column(db.String(100))
    is_custom = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)  # ← Controls live visibility
