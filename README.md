# Codeforces Upcoming Contests API (FastAPI)

Simple FastAPI service that exposes upcoming Codeforces contests. Tested on Linux; depends only on Python 3.10+.

## Setup
1. Create and activate a virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Run locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Then visit http://localhost:8000/contests or the interactive docs at http://localhost:8000/docs.

## API
- `GET /health` — service health probe.
- `GET /contests` — list of upcoming Codeforces contests (cached for 5 minutes to avoid rate limits). Timestamps are in UTC.
   - Optional query params `apiKey` and `apiSecret` let you sign requests with your Codeforces API credentials. Both must be supplied together. Signing is only required for private data; `contest.list` works anonymously.

## Project structure
- `app/main.py` — FastAPI application factory and router wiring.
- `app/api/routes/contests.py` — contests endpoint.
- `app/services/codeforces.py` — Codeforces client, signing, caching.
- `app/services/cache.py` — tiny TTL cache helper.
- `app/dependencies/auth.py` — query param parsing for API key/secret.
- `app/core/config.py` — constants (base URL, cache TTL, timeouts).

## Notes
- Uses the public Codeforces endpoint `https://codeforces.com/api/contest.list?gym=false` and filters by `phase == "BEFORE"`.
- Network errors or non-OK responses (including Codeforces rate limit: 1 request per 2 seconds) are returned as HTTP 502 from this service.
- Adjust cache TTL inside `app/core/config.py` via `CACHE_TTL_SECONDS` if you need fresher data.
- Codeforces API does not expose a "registered contests" list for a user; adding that would require scraping the website, which is not included here.
