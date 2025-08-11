# osu! Lost Scores Backend

FastAPI service behind [api.lemon4ik.kz](https://api.lemon4ik.kz). The backend authenticates players via osu! OAuth, enriches beatmap metadata, stores thin JSON submissions, and serves the web clients at [lemon4ik.kz](https://lemon4ik.kz) and [lost.lemon4ik.kz](https://lost.lemon4ik.kz).

## Features

- osu! OAuth authentication with JWT session management
- Beatmap metadata enrichment with caching (SQLite + WAL)
- Thin JSON submission storage and static asset delivery for the websites
- Maintenance helpers (`python -m app.db.maintenance`) for WAL checkpoints and snapshots

## Local setup

```bash
git clone https://github.com/kz-lemon4ik/lost-scores-backend.git
cd lost-scores-backend

python -m venv .venv
.\.venv\Scripts\activate      # Windows
pip install -r requirements.txt

cp .env.example .env          # fill in osu! credentials + secrets
uvicorn app.main:app --reload --port 8000
```

Interactive docs live at [http://localhost:8000/api/docs](http://localhost:8000/api/docs). Production traffic goes through Cloudflare to `https://api.lemon4ik.kz`.

### Minimal `.env`

```
OSU_CLIENT_ID=...
OSU_CLIENT_SECRET=...
OSU_REDIRECT_URI=http://127.0.0.1:8000/api/auth/callback

SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

SESSION_COOKIE_NAME=lost_scores_session
SESSION_COOKIE_EXPIRE_SECONDS=86400

DATABASE_URL=sqlite:///./storage/database.db

HMAC_SECRET_KEY=...
```

## Handy commands

```bash
uvicorn app.main:app --reload
python -m app.db.maintenance info
python -m app.db.maintenance checkpoint --mode FULL
python -m app.db.maintenance snapshot --output storage/database_snapshot.db
pytest            # once tests are added
```

## Structure

```
app/
  api/        - routers and dependencies
  core/       - config, osu! client, security utilities
  crud/       - database queries
  models/     - SQLAlchemy models
  schemas/    - Pydantic DTOs
  main.py
alembic/      - migrations
storage/      - SQLite artefacts (ignored in git)
```

Questions or suggestions? Open an issue or reach out directly (osu! / Telegram).
