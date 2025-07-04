from flask import Flask, jsonify, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from models import db, NewsArticle
import feedparser
import re
import os
from datetime import datetime, timedelta
from dateutil import parser
import mimetypes,requests

mimetypes.add_type('application/javascript', '.js')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_dev_key')  # Needed for sessions, set securely in production
# Developer Signature (Do not remove)
_DEVELOPER_SIGNATURE = "Developed by Bikash"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Dummy admin credentials
ADMIN_USERNAME = 'chainlogshots'
ADMIN_PASSWORD = 'phex$63Tan@'

db.init_app(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    db.create_all()

CATEGORY_FEEDS = {
    "daily-news": [
        "https://www.coindesk.com/arc/outboundfeeds/rss",
        "https://cointelegraph.com/rss/tag/blockchain", 
    ],
    "edu": ["https://cointelegraph.com/rss/category/analysis"],
    "btca": ["https://cointelegraph.com/rss/tag/bitcoin"],
}

def summarize(text, word_limit=70):
    clean_text = re.sub('<[^<]+?>', '', text)
    words = clean_text.split()
    return ' '.join(words[:word_limit]) + ('...' if len(words) > word_limit else '')

def fetch_news_by_category(category):
    feeds = CATEGORY_FEEDS.get(category.lower(), CATEGORY_FEEDS['daily-news'])

    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if NewsArticle.query.filter_by(link=entry.link).first():
                continue

            raw_summary = ""
            if hasattr(entry, 'summary') and entry.summary.strip():
                raw_summary = entry.summary
            elif hasattr(entry, 'content') and len(entry.content) > 0:
                raw_summary = entry.content[0].value
            else:
                raw_summary = entry.title

            word_limit = 50 if "coindesk.com" in url else 70
            summary = summarize(raw_summary, word_limit=word_limit)

            image_url = None
            if 'media_content' in entry:
                image_url = entry.media_content[0].get('url')
            else:
                img_match = re.search(r'<img[^>]+src="([^"]+)"', raw_summary)
                if img_match:
                    image_url = img_match.group(1)

            article = NewsArticle(
                title=entry.title,
                link=entry.link,
                published=entry.get('published', ''),
                summary=summary,
                image_url=image_url,
                source=url,
                category=category,
                is_custom=False,
                is_published=True
            )
            db.session.add(article)

    db.session.commit()

    articles = NewsArticle.query.filter_by(category=category, is_published=True).order_by(NewsArticle.id.desc()).limit(100).all()
    return [{
        "title": a.title,
        "link": a.link,
        "published": a.published,
        "summary": a.summary,
        "image_url": a.image_url
    } for a in articles]

@app.route('/')
def index():
    if not session.get('has_seen_welcome'):
        session['has_seen_welcome'] = True
        return redirect(url_for('welcome'))

    '''articles = NewsArticle.query.filter_by(is_published=True).order_by(NewsArticle.id.desc()).limit(100).all()
    return render_template('index.html', articles=articles)'''

    latest_articles = NewsArticle.query.filter_by(is_published=True).order_by(NewsArticle.id.desc()).limit(100).all()
    return render_template('index.html', latest_articles=latest_articles)


@app.route('/custom')
def custom():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('custom_news_uploader.html')

@app.route('/news')
def news():
    category = request.args.get('category', 'daily-news')

    if category == 'for-you':
        articles = NewsArticle.query.filter_by(
            is_custom=True, is_published=True, category="for-you"
        ).order_by(NewsArticle.id.desc()).limit(100).all()
    else:
        latest_article = NewsArticle.query.filter_by(category=category).order_by(NewsArticle.id.desc()).first()

        should_refresh = False
        if not latest_article:
            should_refresh = True
        else:
            try:
                published_time = parser.parse(latest_article.published)
                if datetime.utcnow() - published_time > timedelta(hours=6):
                    should_refresh = True
            except Exception:
                should_refresh = True  # fallback: refresh if parsing fails

        if should_refresh:
            fetch_news_by_category(category)

        articles = NewsArticle.query.filter_by(
            category=category, is_published=True
        ).order_by(NewsArticle.id.desc()).limit(100).all()

    return jsonify([
        {
            "title": a.title,
            "link": a.link,
            "published": a.published,
            "summary": a.summary,
            "image_url": a.image_url
        } for a in articles
    ])

@app.route('/upload-news', methods=['GET', 'POST'])
def upload_news():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'GET':
        return render_template('custom_news_uploader.html')

    title = request.form.get('title')
    link = request.form.get('link')
    published = request.form.get('published')
    summary = request.form.get('summary')
    image_url = request.form.get('image_url')
    image = request.files.get('image')
    category = request.form.get('category', 'for-you')

    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        image_url = '/' + image_path.replace('\\', '/')

    try:
        new_article = NewsArticle(
            title=title,
            link=link,
            published=published,
            summary=summary,
            image_url=image_url,
            source='Custom',
            category=category,
            is_custom=True,
            is_published=True
        )
        db.session.add(new_article)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/edit-article/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    article = NewsArticle.query.get_or_404(article_id)

    if request.method == 'POST':
        article.title = request.form.get('title')
        article.link = request.form.get('link')
        article.published = request.form.get('published')
        article.summary = request.form.get('summary')
        article.image_url = request.form.get('image_url')
        article.source = request.form.get('source')
        article.category = request.form.get('category')
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', article=article)

@app.route('/delete-article/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    article = NewsArticle.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/toggle-publish/<int:article_id>', methods=['POST'])
def toggle_publish(article_id):
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    data = request.get_json()
    article = NewsArticle.query.get_or_404(article_id)
    article.is_published = data.get('published', False)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/refresh-news', methods=['POST'])
def refresh_news():
    category = request.args.get('category')
    
    if not category:
        return jsonify({"success": False, "error": "Category is required."}), 400

    # Optional: validate if it's a known category
    valid_categories = {"daily-news", "edu", "btca", "for-you"}
    if category not in valid_categories:
        return jsonify({"success": False, "error": "Invalid category"}), 400

    # Delete all news in that category
    NewsArticle.query.filter_by(category=category).delete()
    db.session.commit()

    # Re-fetch and store fresh news
    fetch_news_by_category(category)

    return jsonify({"success": True, "message": f"News refreshed for category: {category}"})

# Admin login page
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials', 401
    return render_template('admin_login.html')

# Admin logout
@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Protect Dashboard
@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    articles = NewsArticle.query.all()
    return render_template('dashboard.html', articles=articles)

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')



if __name__ == '__main__':
    app.run(debug=True)
