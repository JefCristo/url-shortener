# main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
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
    short_code = Column(String(50), unique=True, index=True, nullable=False)  # Increased for custom codes
    long_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    clicks = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# ========== REDIS SETUP ==========
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# ========== FASTAPI APP ==========
app = FastAPI(title="URL Shortener")

# ========== STATIC FILES (CSS) ==========
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

# ========== WEB INTERFACE (with external CSS and custom code support) ==========
@app.get("/", response_class=HTMLResponse)
def web_interface():
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Shortener - Make your links tiny!</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <div class="subtitle">Make your long URLs short and shareable</div>

        <div class="input-group">
            <label for="longUrl">Enter your long URL:</label>
            <input type="url" id="longUrl" placeholder="https://example.com/very/long/url" autocomplete="off">
        </div>

        <div class="input-group">
            <label for="customCode">Custom short code (optional):</label>
            <input type="text" id="customCode" placeholder="e.g., mylink (letters and numbers only)" autocomplete="off">
            <small style="color: #666; display: block; margin-top: 5px;">Leave blank for random code</small>
        </div>

        <button onclick="shortenUrl()">✨ Shorten URL</button>
        <div id="result" class="result"></div>
        <div class="footer">⚡ Powered by FastAPI, Redis & PostgreSQL</div>
    </div>

    <script>
        async function shortenUrl() {
            const longUrlInput = document.getElementById('longUrl');
            const longUrl = longUrlInput.value.trim();
            const customCode = document.getElementById('customCode').value.trim();
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '';
            resultDiv.classList.remove('show');
            
            if (!longUrl) {
                showError('Please enter a URL');
                return;
            }
            
            resultDiv.innerHTML = '<div class="loading">⏳ Shortening your URL...</div>';
            resultDiv.classList.add('show');
            
            try {
                let url = `/shorten?long_url=${encodeURIComponent(longUrl)}`;
                if (customCode) {
                    url += `&custom_code=${encodeURIComponent(customCode)}`;
                }
                const response = await fetch(url);
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.detail || 'Something went wrong');
                
                resultDiv.innerHTML = `
                    <div style="font-weight: 600; margin-bottom: 10px;">✅ Your shortened URL is ready!</div>
                    <div class="short-url">
                        📎 <strong>Short URL:</strong><br>
                        <a href="${data.short_url}" target="_blank">${data.short_url}</a>
                    </div>
                    <div class="short-url">
                        🔗 <strong>Original URL:</strong><br>
                        ${escapeHtml(data.long_url)}
                    </div>
                    <div class="stats-link">
                        📊 <a href="/stats/${data.short_code}" target="_blank">View statistics</a>
                    </div>
                `;
                longUrlInput.value = '';
                document.getElementById('customCode').value = '';
            } catch (error) {
                showError(error.message);
            }
        }
        
        function showError(message) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `<div class="error">❌ Error: ${escapeHtml(message)}</div>`;
            resultDiv.classList.add('show');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        document.getElementById('longUrl').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') shortenUrl();
        });
        document.getElementById('customCode').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') shortenUrl();
        });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)

# ========== API ENDPOINTS ==========
@app.api_route("/shorten", methods=["GET", "POST"])
def shorten_url(long_url: str, custom_code: str = None, db: Session = Depends(get_db)):
    # Auto-add https:// if missing
    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url
    
    # Use custom code if provided, otherwise generate random
    if custom_code:
        # Validate custom code (only letters and numbers)
        if not custom_code.isalnum():
            raise HTTPException(status_code=400, detail="Custom code must contain only letters and numbers")
        
        # Check if custom code already exists
        existing = db.query(URL).filter(URL.short_code == custom_code).first()
        if existing:
            raise HTTPException(status_code=400, detail="Custom code already taken. Choose another.")
        short_code = custom_code
    else:
        short_code = generate_short_code()
    
    # Save to database
    new_url = URL(short_code=short_code, long_url=long_url)
    db.add(new_url)
    db.commit()
    db.refresh(new_url)
    
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