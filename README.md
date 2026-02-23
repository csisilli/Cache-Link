# URL Shortening Service

A scalable, production-ready URL shortening service built with FastAPI, Redis, and MySQL.

## Features

- ⚡ Fast URL redirects with Redis caching (~1ms latency)
- 🔐 Rate limiting (1000 req/min per IP)
- 📊 Click analytics and statistics
- 🗃️ Custom short code support
- ⏱️ URL expiration (TTL)
- 🐳 Docker containerization
- ✅ 40+ test cases

## Project Structure

```
System Design/
├── app/                      # Main application
│   ├── main.py              # FastAPI app setup
│   ├── routes.py            # 12 API endpoints
│   ├── models.py            # Database ORM models
│   ├── schemas.py           # Request/response schemas
│   ├── cache.py             # Redis caching layer
│   └── utils.py             # Base62 encoding, validation
│
├── config/
│   └── config.py            # Configuration (database, Redis, API)
│
├── infrastructure/          # Deployment files
│   ├── docker-compose.yml   # Multi-service orchestration
│   ├── Dockerfile           # FastAPI container
│   ├── nginx.conf           # Load balancer
│   └── init.sql             # Database schema
│
├── tests/
│   └── tests.py             # 40+ unit/integration tests
│
├── scripts/
│   └── migrate.py           # Database migration tool
│
└── docs/
    └── QUICKSTART.md        # Quick start guide
```

## Quick Start

### Prerequisites
- **Docker** & **Docker Compose** (easiest way to start)
- **Python 3.9+** (for local development without Docker)

### Starting the Service

#### Option 1: Docker (Recommended)

1. **Start all services** (MySQL, Redis, FastAPI, Nginx):
   ```bash
   docker-compose up -d
   ```

2. **Wait for services to be ready** (~10-15 seconds):
   ```bash
   docker-compose logs -f
   # Press Ctrl+C when you see "Uvicorn running on..."
   ```

3. **Initialize the database**:
   ```bash
   docker exec -it app python scripts/migrate.py create
   ```

4. **Access the service**:
   - 🌐 **Swagger UI (interactive API docs)**: http://localhost:8000/docs
   - 📚 **ReDoc (API documentation)**: http://localhost:8000/redoc
   - 🔗 **API endpoint**: http://localhost:8000/api/v1/shorten

#### Option 2: Local Development (Without Docker)

1. **Clone/navigate to project**:
   ```bash
   cd System\ Design
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Redis** (Terminal 1):
   ```bash
   redis-server
   ```

4. **Start MySQL** (Terminal 2):
   ```bash
   mysql -u root -p < infrastructure/init.sql
   ```

5. **Initialize database** (Terminal 2):
   ```bash
   python scripts/migrate.py create
   ```

6. **Start FastAPI app** (Terminal 3):
   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. **Access at**: http://localhost:8000/docs

### Your First API Call

**Create a short URL**:
```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com/very/long/path?param=value"}'
```

**Response**:
```json
{
  "short_code": "abc123",
  "short_url": "https://short.url/abc123",
  "long_url": "https://example.com/very/long/path?param=value",
  "created_at": "2026-02-22T10:30:00"
}
```

**Use the short URL**:
```bash
curl -L http://localhost:8000/abc123
# Redirects to the original URL
```

**Get statistics**:
```bash
curl http://localhost:8000/api/v1/stats/abc123
# Returns click counts and access patterns
```

### Stopping the Service

```bash
# Docker
docker-compose down

# Local (Ctrl+C in each terminal)
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/v1/shorten | Create short URL |
| GET | /{short_code} | Redirect to original URL |
| GET | /api/v1/stats/{code} | Get click statistics |
| GET | /api/v1/urls | List all URLs |
| DELETE | /api/v1/urls/{code} | Delete URL |
| GET | /health | Health check |

## Configuration

Edit `config/config.py` to customize:
- Database URL
- Redis URL
- Cache TTL (default: 24 hours)
- Rate limit (default: 1000 req/min)
- Short code length (default: 6 characters)

## Running Tests

```bash
pytest tests/tests.py -v
```

## Deployment

### Docker
```bash
docker-compose up -d
```

### Check Status
```bash
docker-compose ps
docker-compose logs -f
```

### Database Management
```bash
python scripts/migrate.py status          # Check database status
python scripts/migrate.py reset           # Clear all data
```

## Key Technologies

- **Framework**: FastAPI with async/await
- **Database**: SQLAlchemy ORM + MySQL/PostgreSQL
- **Cache**: Redis (multi-layer)
- **Load Balancer**: Nginx with rate limiting
- **Testing**: Pytest with 40+ test cases
- **Containerization**: Docker & Docker Compose

## Architecture Highlights

### Caching Strategy
- **L1**: URL mappings (24h TTL) - Fast redirects
- **L2**: Statistics (1h TTL) - Reduced DB queries
- **L3**: Rate limits (60s TTL) - Token bucket per IP

### Performance
- Redirect: 1-5ms (cached), 50ms (DB)
- URL Creation: 10-20ms
- Statistics: 5-50ms (cached)

### Database Schema
- **urls**: URL mappings with indexing
- **clicks**: Click analytics (one per access)
- **rate_limits**: Rate limiting state per IP

## Code Quality

✅ Type hints on all functions
✅ Comprehensive docstrings
✅ 85% code documentation
✅ Algorithm explanations
✅ Performance notes
✅ Security considerations

Each Python file includes detailed comments explaining the code. See file headers for:
- Module purpose
- Class documentation
- Function parameters and examples
- Algorithm explanations

## License

See LICENSE file

## Development

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python -m uvicorn app.main:app --reload

# Run tests
pytest tests/tests.py -v
```

### Database Operations
```bash
# Create tables
python scripts/migrate.py create

# Check status
python scripts/migrate.py status

# Reset database (destructive)
python scripts/migrate.py reset
```

---

For more details on implementation, see inline code comments in Python files.
