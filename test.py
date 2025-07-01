import requests

def fetch_news_by_category(category):
    feeds = CATEGORY_FEEDS.get(category.lower(), CATEGORY_FEEDS['daily-news'])

    for url in feeds:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0; +http://yourwebsite.com)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Error fetching/parsing feed {url}: {e}")
            continue

        for entry in feed.entries:
            # Skip duplicates
            if NewsArticle.query.filter_by(link=entry.link).first():
                continue

            # Extract content (prefer full body for CoinDesk)
            if hasattr(entry, 'content') and entry.content and 'value' in entry.content[0]:
                raw_summary = entry.content[0]['value']
            elif hasattr(entry, 'summary') and entry.summary.strip():
                raw_summary = entry.summary
            else:
                raw_summary = entry.title

            # Word limit (CoinDesk gets shorter summaries)
            word_limit = 50 if "coindesk.com" in url else 70
            summary = summarize(raw_summary, word_limit=word_limit)

            # Extract image
            image_url = None
            if hasattr(entry, 'media_content') and entry.media_content:
                image_url = entry.media_content[0].get('url')
            else:
                img_match = re.search(r'<img[^>]+src="([^"]+)"', raw_summary)
                if img_match:
                    image_url = img_match.group(1)

            # Save article
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

    # Return latest articles from DB
    articles = NewsArticle.query.filter_by(
        category=category, is_published=True
    ).order_by(NewsArticle.id.desc()).limit(100).all()

    return [{
        "title": a.title,
        "link": a.link,
        "published": a.published,
        "summary": a.summary,
        "image_url": a.image_url
    } for a in articles]
