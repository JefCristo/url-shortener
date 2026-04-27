# URL Shortener Service

A high-performance URL shortener built with FastAPI, PostgreSQL, and Redis. Shorten long URLs, track clicks, and get instant redirects with caching for speed.

## Features

- Shorten URLs - Create short links via web interface or API
- Click Tracking - Count how many times each short link is visited
- Fast Redirects - Redis caching makes popular links load instantly
- Auto HTTPS - Adds https:// automatically if you forget
- REST API - Use programmatically for integrations
- Responsive UI - Clean, modern interface that works on all devices

## Tech Stack

- FastAPI - Web framework for API and web interface
- PostgreSQL - Permanent URL storage
- Redis (Memurai) - Caching for fast lookups
- Uvicorn - ASGI server
- HTML/CSS/JS - Frontend interface

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

	Open pgAdmin 4 and run:

	```sql
	CREATE DATABASE url_shortener;
	```

5. Configure database connection

	Edit `main.py` and update this line with your PostgreSQL password:

	```python
	DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost/url_shortener"
	```

6. Start Redis

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

- `GET/POST /shorten?long_url=URL` - Create short URL
- `GET /short_code` - Redirect to original URL
- `GET /stats/short_code` - Get click statistics

## API Response Examples

Create short URL response:

```json
{"short_code": "aB3Xy9", "short_url": "http://localhost:8000/aB3Xy9", "long_url": "https://www.google.com"}
```

Get statistics response:

```json
{"short_code": "aB3Xy9", "long_url": "https://www.google.com", "clicks": 42, "created_at": "2026-04-27T12:07:56.386859"}
```

## Project Structure

```text
url-shortener/
├── main.py
├── models.py
├── test_connection.py
├── static/
│   └── style.css
├── requirements.txt
├── .gitignore
└── README.md
```

## Troubleshooting

- Database does not exist - Create the database in pgAdmin first
- Redis connection refused - Run `memurai-cli ping` to check if Redis is running
- Port 8000 already in use - Change port in `main.py` to 8001
- PostgreSQL connection failed - Check PostgreSQL is running and password is correct

## Future Improvements

- Custom short codes
- QR code generation
- URL expiration dates
- User accounts and authentication
- Advanced analytics
- Docker containerization

## License

GNU General Public License (GPL) - see LICENSE file for details.

## Author

JefCristo

GitHub: https://github.com/JefCristo

Built with FastAPI, PostgreSQL, Redis, and coffee