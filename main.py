# main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates   # optional – you can keep raw HTML if preferred
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import random
import string
import redis

# ========== DATABASE SETUP ==========
DATABASE_URL = "postgresql://postgres:postgres@localhost/url_shortener"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(50), unique=True, index=True, nullable=False)
    long_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    clicks = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# ========== REDIS SETUP ==========
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# ========== FASTAPI APP ==========
app = FastAPI(title="URL Shortener")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_random_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def create_unique_random_code(db: Session, length=6, max_attempts=5):
    """Generate a random code not present in DB. Increase length if collisions occur."""
    for attempt in range(max_attempts):
        code = generate_random_code(length)
        if not db.query(URL).filter(URL.short_code == code).first():
            return code
    # If still colliding, try longer code recursively
    return create_unique_random_code(db, length + 1, max_attempts)

# ========== WEB INTERFACE ==========
@app.get("/", response_class=HTMLResponse)
def web_interface():
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Shortener</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <div class="subtitle">Shorten URLs with custom codes</div>

        <div class="input-group">
            <label for="longUrl">Long URL:</label>
            <input type="url" id="longUrl" placeholder="https://example.com/very/long/url">
        </div>

        <div class="input-group">
            <label for="customCode">Custom short code (optional):</label>
            <input type="text" id="customCode" placeholder="e.g., mylink (alphanumeric only)">
            <small>Leave blank for random code</small>
        </div>

        <button onclick="shortenUrl()">✨ Shorten URL</button>
        <div id="result" class="result"></div>
        <div class="footer">⚡ FastAPI · PostgreSQL · Redis</div>
    </div>

    <script>
        async function shortenUrl() {
            const longUrl = document.getElementById('longUrl').value.trim();
            const customCode = document.getElementById('customCode').value.trim();
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '';
            resultDiv.classList.remove('show');
            if (!longUrl) { showError('Please enter a URL'); return; }

            resultDiv.innerHTML = '<div class="loading">⏳ Shortening...</div>';
            resultDiv.classList.add('show');

            try {
                let url = `/shorten?long_url=${encodeURIComponent(longUrl)}`;
                if (customCode) url += `&custom_code=${encodeURIComponent(customCode)}`;
                const response = await fetch(url);
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail);
                resultDiv.innerHTML = `
                    <div class="short-url">✅ Short URL: <a href="${data.short_url}" target="_blank">${data.short_url}</a></div>
                    <div class="short-url">🔗 Original: ${escapeHtml(data.long_url)}</div>
                    <div class="stats-link">📊 <a href="/stats/${data.short_code}" target="_blank">Statistics</a></div>
                `;
                document.getElementById('longUrl').value = '';
                document.getElementById('customCode').value = '';
            } catch (err) { showError(err.message); }
        }
        function showError(msg) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `<div class="error">❌ ${escapeHtml(msg)}</div>`;
            resultDiv.classList.add('show');
        }
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        document.getElementById('longUrl').addEventListener('keypress', e => e.key === 'Enter' && shortenUrl());
        document.getElementById('customCode').addEventListener('keypress', e => e.key === 'Enter' && shortenUrl());
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

# ========== API ENDPOINTS ==========
@app.api_route("/shorten", methods=["GET", "POST"])
def shorten_url(long_url: str, custom_code: str = None, db: Session = Depends(get_db)):
    # Auto-add https://
    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url

    # Handle custom code
    if custom_code:
        if not custom_code.isalnum():
            raise HTTPException(status_code=400, detail="Custom code must contain only letters and numbers")
        if len(custom_code) > 50:
            raise HTTPException(status_code=400, detail="Custom code too long (max 50 chars)")
        # Check existence
        existing = db.query(URL).filter(URL.short_code == custom_code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Custom code already taken")
        short_code = custom_code
    else:
        short_code = create_unique_random_code(db)   # collision-safe

    # Create and save
    new_url = URL(short_code=short_code, long_url=long_url)
    try:
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
    except IntegrityError:   # In case of a very unlucky race condition
        db.rollback()
        if not custom_code:
            short_code = create_unique_random_code(db, length=7)  # longer fallback
            new_url = URL(short_code=short_code, long_url=long_url)
            db.add(new_url)
            db.commit()
            db.refresh(new_url)
        else:
            raise HTTPException(status_code=409, detail="Conflict. Try a different custom code.")

    # Cache in Redis
    redis_client.setex(f"url:{short_code}", 3600, long_url)

    return {
        "short_code": short_code,
        "short_url": f"http://localhost:8000/{short_code}",
        "long_url": long_url
    }

@app.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):
    long_url = redis_client.get(f"url:{short_code}")
    if not long_url:
        url_entry = db.query(URL).filter(URL.short_code == short_code).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="URL not found")
        long_url = url_entry.long_url
        url_entry.clicks += 1
        db.commit()
        redis_client.setex(f"url:{short_code}", 3600, long_url)
    else:
        # Still update click count in background (async would be better, but fine)
        url_entry = db.query(URL).filter(URL.short_code == short_code).first()
        if url_entry:
            url_entry.clicks += 1
            db.commit()
    return RedirectResponse(url=long_url, status_code=307)

@app.get("/stats/{short_code}")
def get_stats(short_code: str, db: Session = Depends(get_db)):
    url_entry = db.query(URL).filter(URL.short_code == short_code).first()
    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    return {
        "short_code": url_entry.short_code,
        "long_url": url_entry.long_url,
        "clicks": url_entry.clicks,
        "created_at": url_entry.created_at
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)