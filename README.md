# osu! Lost Scores Backend

Backend API for the osu! Lost Scores analyzer application. Handles user authentication through osu! OAuth, manages analysis report submissions, and provides hall of fame functionality.

## Features

- osu! OAuth authentication
- Report upload and management
- Hall of Fame leaderboards
- Secure osu! API proxy
- JWT session management
- HMAC file verification

## Tech Stack

- FastAPI framework
- SQLite database with SQLAlchemy ORM
- JWT + osu! OAuth authentication
- HMAC signature verification
- pytest for testing

## Installation

### Prerequisites

- Python 3.8 or higher
- osu! API application credentials

### Setup Steps

1. Clone the repository
   ```bash
   git clone https://github.com/kz-lemon4ik/lost-scores-backend.git
   cd lost-scores-backend
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Set up osu! OAuth Application
   - Visit osu! Account Settings OAuth section
   - Create new OAuth application
   - Set redirect URI to `http://127.0.0.1:8000/api/auth/callback`
   - Add Client ID and Client Secret to your .env file

5. Generate secret keys
   ```bash
   # Generate SECRET_KEY
   openssl rand -hex 32
   
   # Generate HMAC_SECRET_KEY
   openssl rand -hex 32
   ```

## Configuration

Create a `.env` file with these variables:

```env
# osu! OAuth Credentials
OSU_CLIENT_ID="your_osu_client_id"
OSU_CLIENT_SECRET="your_osu_client_secret"
OSU_REDIRECT_URI="http://127.0.0.1:8000/api/auth/callback"

# JWT Configuration
SECRET_KEY="your_secret_key_here"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Session Configuration
SESSION_COOKIE_NAME=lost_scores_session
SESSION_COOKIE_EXPIRE_SECONDS=86400

# Database
DATABASE_URL="sqlite:///./storage/database.db"

# HMAC Security
HMAC_SECRET_KEY="your_hmac_secret_key_here"
```

## Development

### Running the Server

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, access documentation at:
- Interactive docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Verbose output
pytest -v
```

## Project Structure

```
lost-scores-backend/
├── app/
│   ├── api/
│   │   ├── endpoints/          # API route handlers
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── hall_of_fame.py # Hall of fame endpoints
│   │   │   └── proxy.py       # osu! API proxy
│   │   ├── api.py             # API router
│   │   └── deps.py            # Dependency injection
│   ├── core/
│   │   ├── config.py          # Configuration settings
│   │   ├── osu_api_client.py  # osu! API client
│   │   └── security.py        # Security utilities
│   ├── crud/                  # Database operations
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas
│   └── main.py               # FastAPI application
├── tests/                     # Test files
├── storage/                   # Data storage
│   ├── database.db           # SQLite database
│   ├── replays/              # Uploaded replay files
│   └── reports/              # Analysis reports
├── requirements.txt
└── .env.example
```

## API Endpoints

### Authentication
- `GET /api/auth/login` - Start osu! OAuth flow
- `GET /api/auth/callback` - Handle OAuth callback
- `POST /api/auth/logout` - Logout user

### Hall of Fame
- `GET /api/hall_of_fame/submissions` - Get top submissions
- `POST /api/hall_of_fame/submit` - Submit analysis report
- `GET /api/hall_of_fame/download/{submission_id}/{filename}` - Download replay

### Proxy
- `GET /api/proxy/users/{user_id}` - Get osu! user data

## Security Features

- CORS protection for specific origins
- JWT session management
- HMAC report verification
- Safe file handling
- SQL injection prevention

## Testing

Includes comprehensive tests for authentication, API endpoints, security, and database operations. Test files are in the `tests/` directory using pytest with FastAPI's testing client.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Author

**Lemon4ik**
- Website: [lemon4ik.kz](https://lemon4ik.kz)
- GitHub: [@kz-lemon4ik](https://github.com/kz-lemon4ik)
- osu!: [lemon4ik_kz](https://osu.ppy.sh/users/8674298)

## Related Projects

- [Lost Scores Frontend](https://github.com/kz-lemon4ik/lemon-site) - React frontend for the web interface
- [Lost Scores Analyzer](https://github.com/kz-lemon4ik/pp-scam) - Desktop application for analyzing replays