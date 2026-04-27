# main.py
import os
import socket
import random
import string
import redis
import qrcode
from io import BytesIO
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError

# ========== ENVIRONMENT CONFIGURATION ==========
# Detect if running locally or in production
IS_PRODUCTION = os.environ.get("RENDER", False) or os.environ.get("RAILWAY", False)

# Database URL (from environment variable or local default)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost/url_shortener"
)

# Redis URL (from environment variable or local default)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Base URL for QR codes (from environment or auto-detect)
if IS_PRODUCTION:
    BASE_URL = os.environ.get("BASE_URL", "https://your-app.onrender.com")
else:
    # Auto-detect local IP for QR codes on WiFi
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
    BASE_URL = os.environ.get("BASE_URL", f"http://{get_local_ip()}:8000")

print(f"Running in {'PRODUCTION' if IS_PRODUCTION else 'LOCAL'} mode")
print(f"Database: {DATABASE_URL[:50]}...")
print(f"Base URL: {BASE_URL}")

# ========== DATABASE SETUP ==========
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

# Create tables (if not exists)
Base.metadata.create_all(bind=engine)

# ========== REDIS SETUP ==========
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ========== FASTAPI APP ==========
app = FastAPI(title="URL Shortener")

# Mount static files (only if static folder exists locally)
if os.path.exists("static"):
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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 0.9em; }
        .input-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 500; }
        input {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            display: none;
            animation: slideUp 0.3s ease-out;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .result.show { display: block; }
        .short-url {
            background: white;
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            word-break: break-all;
        }
        .short-url a { color: #667eea; text-decoration: none; font-weight: 600; }
        .short-url a:hover { text-decoration: underline; }
        .stats-link { margin-top: 10px; font-size: 0.9em; }
        .stats-link a { color: #764ba2; text-decoration: none; }
        .error { background: #fee; color: #c33; padding: 10px; border-radius: 8px; margin-top: 10px; }
        .loading { text-align: center; margin-top: 20px; color: #667eea; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 0.8em; }
        .qr-code { margin-top: 15px; text-align: center; }
        .qr-code img { margin-top: 10px; border: 1px solid #ddd; border-radius: 8px; padding: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <div class="subtitle">Shorten URLs with custom codes + QR codes</div>

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
        <div class="footer">⚡ FastAPI · PostgreSQL · Redis · QR Codes</div>
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
                    <div class="qr-code">
                        <strong>📱 QR Code:</strong><br>
                        <img src="/qr/${data.short_code}" alt="QR Code">
                        <br>
                        <small>Scan with your phone camera</small>
                    </div>
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
        short_code = create_unique_random_code(db)

    # Create and save
    new_url = URL(short_code=short_code, long_url=long_url)
    try:
        db.add(new_url)
        db.commit()
        db.refresh(new_url)
    except IntegrityError:
        db.rollback()
        if not custom_code:
            short_code = create_unique_random_code(db, length=7)
            new_url = URL(short_code=short_code, long_url=long_url)
            db.add(new_url)
            db.commit()
            db.refresh(new_url)
        else:
            raise HTTPException(status_code=409, detail="Conflict. Try a different custom code.")

    # Cache in Redis (1 hour TTL)
    redis_client.setex(f"url:{short_code}", 3600, long_url)

    return {
        "short_code": short_code,
        "short_url": f"{BASE_URL}/{short_code}",
        "long_url": long_url
    }

@app.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):
    # Try Redis cache first
    long_url = redis_client.get(f"url:{short_code}")
    
    if not long_url:
        # Check database
        url_entry = db.query(URL).filter(URL.short_code == short_code).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="URL not found")
        long_url = url_entry.long_url
        # Update click count
        url_entry.clicks += 1
        db.commit()
        # Cache for next time
        redis_client.setex(f"url:{short_code}", 3600, long_url)
    else:
        # Still need to update click count in DB
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

@app.get("/qr/{short_code}")
def generate_qr(short_code: str, db: Session = Depends(get_db)):
    """Generate QR code for a short URL"""
    # Verify the short code exists
    url_entry = db.query(URL).filter(URL.short_code == short_code).first()
    if not url_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    
    # Create the full URL using the base URL
    full_url = f"{BASE_URL}/{short_code}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(full_url)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    
    # Return as image
    return StreamingResponse(img_bytes, media_type="image/png")

# ========== HEALTH CHECK ENDPOINT ==========
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        # Check Redis
        redis_client.ping()
        
        return {"status": "healthy", "database": "connected", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)