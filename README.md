# URL Auditor

A web tool that takes any URL and returns a structured audit report — HTTP status, response time, page title, meta description, SEO metrics, and accessibility checks.

**GitHub Repository**: [https://github.com/Arachno-Sapien/URL-Auditor]

**Live Demo**: [https://url-auditor-kli9.onrender.com]

**Loom Walkthrough**: [https://www.loom.com/share/54c8436333d142a2ab5a9983d7f054be]

---

## Quick Start

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone the repo
git clone https://github.com/Arachno-Sapien/URL-Auditor.git
cd URL-Auditor

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server
python run.py
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment Variables (optional)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `3000` | Server port |
| `FLASK_DEBUG` | `true` | Enable Flask debug mode |
| `AUDITOR_DB_PATH` | `audits.db` | Path to SQLite database file |

---

## API Contract

### `POST /audit`

Accepts a URL and returns a structured page audit report.

#### Request

```json
{
  "url": "https://example.com"
}
```

**Content-Type**: `application/json`

#### Success Response — `200 OK`

```json
{
  "success": true,
  "data": {
    "url": "https://example.com",
    "status_code": 200,
    "response_time_ms": 342,
    "title": "Example Domain",
    "meta_description": "This domain is for use in illustrative examples.",
    "h1_count": 1,
    "total_images": 3,
    "images_missing_alt": 1,
    "word_count": 256
  }
}
```

#### Error Responses

All error responses follow the same shape:

```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

| Status Code | Scenario | Example Error Message |
|---|---|---|
| `400` | Malformed or missing URL | "Invalid URL format. Please provide a full URL starting with http:// or https://" |
| `422` | Non-HTML content (PDF, image, JSON) | "The URL returned \"application/pdf\", not an HTML page. Only HTML pages can be audited." |
| `502` | DNS failure, connection refused, SSL error | "Could not resolve the domain. Check the URL and try again." |
| `504` | Timeout (site took >8s to respond) | "The site took too long to respond (>8s). Try again or check the URL." |
| `500` | Unexpected server error | "Something went wrong on our end. Please try again." |

---

## Running Tests

```bash
pytest -v
```

All tests pass with a single command. No external services or API keys needed.

**Test coverage:**
- `tests/test_validator.py` — 15 tests covering valid URLs, malformed input, non-http protocols, empty input
- `tests/test_parser.py` — 12 tests covering HTML parsing, missing fields, word count accuracy, alt text detection
- `tests/test_audit.py` — 7 integration tests for the `/audit` endpoint with mocked HTTP

---

## Design Decisions

### 1. Python + Flask over a heavier framework (Django, FastAPI)

**Tradeoff**: Django brings an ORM, admin panel, and auth out of the box — but it's a sledgehammer for a single-endpoint tool. FastAPI would give us auto-generated OpenAPI docs and async support, but adds complexity (Pydantic models, async runtime) that isn't justified for a tool with one endpoint that makes one outbound HTTP call.

**Why Flask**: It's the thinnest possible layer between "receive a request" and "return a response." The entire route handler is ~40 lines. Flask also serves static files natively, so I don't need a separate frontend deployment. The result is a single process that handles everything, deployable to any free tier with zero configuration.

### 2. 8-second timeout (not 5s, not 30s)

**Tradeoff**: A 5-second timeout would fail on legitimate but slower sites (government sites, some international CDNs). A 30-second timeout means a user stares at a spinner wondering if the tool is broken, and a burst of slow-site audits could exhaust the server's connection pool.

**Why 8s**: It's long enough to handle most real-world sites (even behind a CDN or with cold starts) but short enough that the user gets fast feedback. The timeout is on the outbound `requests.get` call, not the overall request handling, so our own processing time doesn't eat into it.

### 3. SQLite for audit logging (demonstrating SQL without external infrastructure)

**Tradeoff**: A production audit tool would use PostgreSQL or MySQL for concurrent write safety and horizontal scaling. But requiring a database server means the developer needs Docker or a cloud DB instance just to run locally — that's a terrible DX tradeoff for a tool that might see 10 requests per minute.

**Why SQLite**: It ships with Python, requires zero setup, and handles the read/write volume of this tool easily. WAL mode gives reasonable concurrent read performance. Every audit (success or failure) gets logged with a timestamp, so you can query audit history with plain SQL: `SELECT * FROM audits WHERE url LIKE '%example.com%' ORDER BY audited_at DESC`. If this needed to scale, swapping to PostgreSQL via SQLAlchemy would be a ~30 minute change.

---

## Deployment (Render)

### One-click deploy

1. Push the repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render will auto-detect the `render.yaml` and configure everything
5. Deploy

### Manual configuration

| Setting | Value |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn run:app` |
| Environment | Python 3 |

---

## Project Structure

```
url-auditor/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes.py            # POST /audit endpoint
│   ├── validator.py         # URL validation
│   ├── parser.py            # HTML parsing (BeautifulSoup)
│   ├── fetcher.py           # HTTP fetching with timeout
│   ├── errors.py            # Custom exception classes
│   ├── database.py          # SQLite audit logging
│   └── static/
│       ├── index.html       # Frontend page
│       ├── style.css        # Styling
│       └── app.js           # Client-side logic
├── tests/
│   ├── test_validator.py    # Validator unit tests
│   ├── test_parser.py       # Parser unit tests
│   └── test_audit.py        # Endpoint integration tests
├── run.py                   # Entry point
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment config
├── .gitignore
└── README.md
```

---

## Credits

Built for [Digital Heroes Training Task](https://digitalheroesco.com)
