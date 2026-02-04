# 🔗 URL Shortener

A scalable URL shortening service that converts long URLs to short, memorable codes and handles millions of daily requests with sub-100ms latency.

## Features

⚡ **High-Performance URL Shortening**
- Convert long URLs to 6-7 character short codes
- Redirect latency under 100ms with Redis caching
- Support for millions of requests per day (100M+)
- Base62 encoding supports ~56 billion unique URLs

🚀 **Scalability & Performance**
- Horizontal scaling with load balancers (10-20+ app servers)
- Multi-layer caching with Redis for hot URLs
- Database read replicas for analytics queries
- Automatic sharding for massive scale
- CDN integration for global edge redirects

📊 **Analytics & Tracking**
- Track click counts and access patterns
- Per-URL statistics (total clicks, clicks per day)
- User URL management and history
- JSON persistence for user data

⚙️ **Enterprise Features**
- Custom short URL aliases support
- URL expiration and TTL management
- Rate limiting (token bucket algorithm)
- SQL injection prevention with parameterized queries
- HTTPS/TLS encryption for all traffic

🛡️ **Security & Reliability**
- DDoS protection with WAF + CDN integration
- Master-slave database replication with automatic failover
- Multi-region disaster recovery (active-passive)
- Input validation for URL safety
- 99.9% uptime SLA

## Installation

### Prerequisites
- Python 3.8+ or Node.js 14+
- Docker (optional, for containerization)
- MySQL 5.7+ or PostgreSQL 10+
- Redis 5.0+

### Setup

1. **Clone or download the project:**
   ```bash
   git clone https://github.com/yourusername/url-shortener.git
   cd url-shortener
   ```

2. **Install dependencies:**
   ```bash
   # Python
   pip install -r requirements.txt
   
   # Node.js
   npm install
   ```

3. **Configure environment:**
   Create a `.env` file in the project directory:
   ```
   DATABASE_URL=mysql://user:password@localhost:3306/shortener
   REDIS_URL=redis://localhost:6379
   SECRET_KEY=your_secret_key_here
   API_PORT=8000
   ```

4. **Initialize the database:**
   ```bash
   python migrate.py
   ```

5. **Start Redis:**
   ```bash
   redis-server
   ```

6. **Run the application:**
   ```bash
   python main.py
   # or
   npm start
   ```

### Docker Setup (Optional)

```bash
docker-compose up -d
```

This starts MySQL, Redis, and the application automatically.

## Usage

### Running the Service

```bash
# Development
python main.py --debug

# Production
gunicorn app:app --workers 10 --bind 0.0.0.0:8000
```

The service will be available at `http://localhost:8000`

### API Endpoints

#### Create Short URL
**POST** `/api/v1/shorten`

```json
Request:
{
  "long_url": "https://example.com/very/long/path?param=value&other=data",
  "custom_alias": "mylink",
  "expiry_days": 30
}

Response: 201 Created
{
  "short_code": "abc123",
  "short_url": "https://short.url/abc123",
  "long_url": "https://example.com/very/long/path?param=value&other=data",
  "created_at": "2026-02-03T10:30:00Z"
}
```

**Parameters:**
- `long_url` (required) - The URL to shorten
- `custom_alias` (optional) - Custom short code (must be unique)
- `expiry_days` (optional) - Days until URL expires (default: never)

**Examples:**
```bash
# Simple shortening
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://example.com/very/long/path"}'

# With custom alias
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"long_url": "https://example.com", "custom_alias": "mylink"}'
```

#### Redirect to Original URL
**GET** `/{short_code}`

**Response:** 301 Moved Permanently
```
Location: https://example.com/very/long/path
```

**Example:**
```bash
curl -i http://localhost:8000/abc123
# Returns 301 redirect to original URL
```

#### Get URL Statistics
**GET** `/api/v1/stats/{short_code}`

```json
Response: 200 OK
{
  "short_code": "abc123",
  "long_url": "https://example.com/path",
  "created_at": "2026-02-03T10:30:00Z",
  "total_clicks": 5000,
  "clicks_today": 250,
  "clicks_by_day": {
    "2026-02-03": 250,
    "2026-02-02": 350,
    "2026-02-01": 200
  }
}
```

#### Delete Short URL
**DELETE** `/api/v1/urls/{short_code}`

**Response:** 204 No Content

#### List User URLs
**GET** `/api/v1/urls`

```json
Response: 200 OK
{
  "urls": [
    {
      "short_code": "abc123",
      "long_url": "https://example.com/path1",
      "total_clicks": 5000,
      "created_at": "2026-02-03T10:30:00Z"
    },
    {
      "short_code": "xyz789",
      "long_url": "https://example.com/path2",
      "total_clicks": 1200,
      "created_at": "2026-02-02T15:45:00Z"
    }
  ]
}
```

## System Architecture

```
Clients (Web/Mobile)
  ↓
Load Balancer (nginx/HAProxy)
  ↓
App Servers (10-20 instances)
  ├→ Redis Cache (hot URLs - <100ms)
  └→ MySQL/PostgreSQL (persistent storage)
       ├→ Read Replicas (analytics)
       └→ Backups (S3/GCS)
```

## Database Schema

```sql
CREATE TABLE urls (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  short_code VARCHAR(10) UNIQUE NOT NULL,
  long_url VARCHAR(2048) NOT NULL,
  user_id BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NULL,
  clicks INT DEFAULT 0,
  is_custom BOOLEAN DEFAULT FALSE,
  INDEX(short_code),
  INDEX(user_id),
  INDEX(created_at)
);

CREATE TABLE clicks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  short_code VARCHAR(10) NOT NULL,
  ip_address VARCHAR(45),
  user_agent VARCHAR(500),
  referrer VARCHAR(2048),
  clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX(short_code),
  INDEX(clicked_at)
) PARTITION BY RANGE(YEAR_MONTH(clicked_at));
```

## Performance Metrics

### Latency (Redirect Operation)
```
Cache Hit Path (~50ms total):
- Redis lookup:        1-2ms
- Serialization:       0.5ms
- Network (client):    ~50ms

Database Hit Path (~60ms total):
- Database query:      5-10ms
- Cache write:         1ms
- Network (client):    ~50ms

✓ All requests complete in <100ms
```

### Throughput
- Requests/day: 100M
- Requests/second: ~1,200 RPS
- Peak RPS: ~5,000 RPS
- Read/Write ratio: 100:1

## Project Structure

```
url-shortener/
├── app.py                     # Main application entry point
├── main.py                    # Flask/FastAPI application
├── models.py                  # Database models
├── routes.py                  # API endpoints
├── cache.py                   # Redis caching logic
├── utils.py                   # Helper functions (Base62 encoding, etc)
├── migrations/                # Database migrations
├── tests/                     # Unit and integration tests
├── docker-compose.yml         # Docker configuration
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
├── LICENSE                    # MIT License
└── README.md                  # This file
```

See `requirements.txt` for full list with versions.

## Troubleshooting

**Service doesn't start:**
- Check that all environment variables are set in `.env`
- Verify MySQL and Redis are running
- Check database connection: `mysql -u user -p -h localhost shortener`
- Check Redis connection: `redis-cli ping`

**Redirects returning 404:**
- Verify the short code exists in the database
- Check Redis cache is not out of sync
- Review database logs for integrity issues

**Slow redirect times (>100ms):**
- Check Redis connection and performance
- Verify database indexes exist on `short_code` column
- Monitor CPU and memory usage on app servers
- Check network latency to clients

**High memory usage:**
- Adjust Redis TTL settings in configuration
- Review number of cached URLs
- Consider implementing cache eviction policies

**Database connection errors:**
- Verify connection pool settings
- Check maximum connections limit
- Ensure database user has proper permissions
- Review slow query log for bottlenecks

## Scaling Strategy

### Horizontal Scaling
- Deploy multiple app servers behind load balancer
- Use least-connections or round-robin load balancing
- Monitor health checks continuously

### Caching Strategy
- **L1 Cache (Redis)**: Hot URLs with 30-day TTL
- **L2 Cache (Database)**: Cold URLs with indexed lookups
- **L3 Cache (CDN)**: Edge locations for global distribution

### Database Optimization
- Index on `short_code` for fast lookups
- Partition analytics table by date/month
- Connection pooling (50-100 per server)
- Read replicas for analytics queries only

### Sharding (for massive scale)
```
shard_id = hash(short_code) % num_shards
Distributes URLs across multiple database instances
```

## Capacity Planning

| Metric | Value |
|--------|-------|
| Requests/day | 100M |
| Requests/second | ~1,200 RPS |
| Peak RPS | ~5,000 RPS |
| New URLs/day | ~10M |
| Storage (5 years) | ~1.8 TB |
| Daily bandwidth | ~30 GB |

## Cost Estimate (Annual)

| Component | Cost |
|-----------|------|
| Database (RDS, 1TB) | $15,000 |
| Redis Cache (500GB) | $8,000 |
| App Servers (20x) | $50,000 |
| CDN Bandwidth (30GB/day) | $30,000 |
| Load Balancer | $5,000 |
| Monitoring & Logging | $10,000 |
| **Total Annual** | **$118,000** |

## Contributing

Feel free to fork, modify, and improve this project! Some ideas:
- Add QR code generation for short URLs
- Implement custom domain support
- Add URL preview/metadata extraction
- Build analytics dashboard UI
- Implement bulk URL shortening
- Add webhook notifications
- Geographic-based redirect routing
- A/B testing URL variants
