# URL Shortener Service

A production-ready URL shortener built with FastAPI, PostgreSQL, and Redis. Shorten long URLs, use custom short codes, track clicks, and generate QR codes - all through a clean web interface or REST API.

## Features

- Shorten URLs - Get a short link for any long URL
- Custom Short Codes - Choose your own link (e.g., /mylink) instead of random characters
- Click Tracking - Every short URL tracks how many times it's visited
- QR Code Generation - Every short URL gets a scannable QR code automatically
- Fast Redirects - Redis caching makes popular links load instantly
- REST API - Use programmatically for integrations
- Responsive Web Interface - Clean, modern UI that works on desktop and mobile
- Auto HTTPS - Automatically adds https:// if you forget
- Collision Handling - Automatically retries if a random code already exists

## Tech Stack

| Technology | Purpose |
| --- | --- |
| FastAPI | Web framework for API and web interface |
| PostgreSQL | Permanent URL storage |
| Redis (Memurai) | Caching for fast lookups |
| Uvicorn | ASGI server |
| SQLAlchemy | Database ORM |
| qrcode + Pillow | QR code image generation |
| HTML/CSS/JS | Frontend interface |

## Prerequisites

- Python 3.11 or higher
- PostgreSQL installed and running on port 5432
- Redis (Memurai on Windows) installed and running on port 6379

## Installation & Setup

1. Clone the repository

	```bash
	git clone https://github.com/JefCristo/url-shortener.git
	cd url-shortener
	```

2. Create virtual environment

	```bash
	python -m venv venv
	```

	Activate it:

	- Windows: `venv\Scripts\activate`
	- Mac/Linux: `source venv/bin/activate`

3. Install dependencies

	```bash
	pip install -r requirements.txt
	```

4. Set up the database

	Open pgAdmin 4 or run this command in psql:

	```sql
	CREATE DATABASE url_shortener;
	```

5. Configure database connection

	Edit `main.py` and update the database URL with your PostgreSQL password:

	```python
	DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost/url_shortener"
	```

6. Start Redis

	Ensure Redis is running:

	```bash
	memurai-cli ping
	```

	Should return: `PONG`

7. Run the application

	```bash
	python main.py
	```

8. Open your browser

	Navigate to: `http://localhost:8000`

## API Endpoints

| Method | Endpoint | Description | Example |
| --- | --- | --- | --- |
| GET/POST | `/shorten?long_url={url}` | Create a short URL | `/shorten?long_url=https://google.com` |
| GET/POST | `/shorten?long_url={url}&custom_code={code}` | Create with custom code | `/shorten?long_url=https://google.com&custom_code=google` |
| GET | `/{short_code}` | Redirect to original URL | `/google` |
| GET | `/stats/{short_code}` | Get click statistics | `/stats/google` |
| GET | `/qr/{short_code}` | Download QR code as PNG | `/qr/google` |
| GET | `/health` | Health check for monitoring | `/health` |

## API Response Examples

Create short URL response:

```json
{
  "short_code": "aB3Xy9",
  "short_url": "http://localhost:8000/aB3Xy9",
  "long_url": "https://www.google.com"
}
```

Get statistics response:

```json
{
  "short_code": "google",
  "long_url": "https://www.google.com",
  "clicks": 42,
  "created_at": "2026-04-27T12:07:56.386859"
}
```

## Project Structure

```text
url-shortener/
├── main.py              # FastAPI application (all endpoints)
├── static/              # Static files (CSS, images)
│   └── style.css        # Web interface styling
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Database does not exist | Create url_shortener database in pgAdmin first |
| Redis connection refused | Run memurai-cli ping to check if Redis is running |
| Port 8000 already in use | Change port in the last line of main.py to 8001 |
| PostgreSQL connection failed | Check PostgreSQL is running and password is correct |

## Future Improvements

- User accounts and authentication
- URL expiration dates
- Advanced analytics (browser, location, referrer)
- Bulk URL shortening
- Docker containerization

## License

This project is licensed under the GNU General Public License (GPL) - see the LICENSE file for details.

## Author

JefCristo

GitHub: @JefCristo

Project: url-shortener

## Show Your Support

If you found this project helpful, please give it a star on GitHub!

Built with FastAPI, PostgreSQL, Redis, and ☕