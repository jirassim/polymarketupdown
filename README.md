# Polymarket Trading Bot Dashboard

A comprehensive web dashboard for monitoring and controlling multiple Polymarket trading bots with secure Telegram-based registration.

## Features

- **Real-time Monitoring**: Track performance of up to 12 wallets simultaneously
- **Live Statistics**: Volume, transactions, P&L, and win rate charts
- **Wallet Management**: Configure each wallet's trading side (UP/DOWN) and amounts
- **Secure Registration**: Telegram bot for credential submission with auto-deletion
- **Multi-User Support**: Multiple users can register and monitor their own bots
- **WebSocket Updates**: Real-time trade notifications and statistics
- **Docker Deployment**: Easy deployment with Docker Compose

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│                 │────▶│              │────▶│                 │
│   Frontend      │     │    Nginx     │     │   Backend API   │
│   (HTML/JS)     │◀────│   (Proxy)    │◀────│   (FastAPI)     │
│                 │     │              │     │                 │
└─────────────────┘     └──────────────┘     └─────────────────┘
                                                      │
                                                      ▼
                        ┌──────────────────────────────────────┐
                        │                                      │
                        │  ┌─────────────┐  ┌──────────────┐ │
                        │  │             │  │              │ │
                        │  │  Database   │  │  Telegram    │ │
                        │  │  (SQLite)   │  │     Bot      │ │
                        │  │             │  │              │ │
                        │  └─────────────┘  └──────────────┘ │
                        │                                      │
                        │         Trading Bot System          │
                        │                                      │
                        └──────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Telegram Bot Token (get from @BotFather)
- Polymarket API credentials for your wallets

### 2. Clone and Setup

```bash
# Clone the repository
cd /Users/mac/Documents/claude/updownnewclaim/dashboard

# Copy environment template
cp .env.example .env

# Edit .env file with your credentials
nano .env
```

### 3. Configure Environment

Edit `.env` file with your settings:

```env
# Required: Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ENCRYPTION_KEY=your_32_byte_encryption_key_here

# Optional: Change ports if needed
API_BASE_URL=http://localhost:5000/api
FRONTEND_URL=http://localhost:80

# Database (default SQLite, optional PostgreSQL)
DATABASE_URL=sqlite:///dashboard.db
```

### 4. Start Services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 5. Access Dashboard

- Open browser: http://localhost
- Or with user ID: http://localhost/?user=YOUR_USER_ID

## User Registration

### Via Telegram Bot

1. Start conversation with your bot on Telegram
2. Send `/start` command
3. Follow prompts to submit:
   - User ID (unique identifier)
   - Private Key for each wallet
   - API credentials (Key, Secret, Passphrase)
4. Messages auto-delete after 5 seconds for security
5. Receive dashboard URL upon completion

### Registration Flow

```
User ──▶ /start
Bot  ──▶ "Welcome! Please enter your User ID"
User ──▶ USER_12345
Bot  ──▶ "Enter Private Key for Wallet 1"
User ──▶ 0x...
Bot  ──▶ [Auto-deletes] "Enter API Key for Wallet 1"
...
Bot  ──▶ "Registration complete! Dashboard: http://localhost/?user=USER_12345"
```

## Dashboard Features

### 1. Main Overview
- Total volume (24h)
- Active positions count
- Total P&L
- Win rate percentage
- Real-time charts

### 2. Wallet Cards
Each wallet displays:
- Wallet number and address
- Position (UP/DOWN)
- Current balance
- Daily volume
- Open positions
- Status indicator (Active/Inactive)

### 3. Wallet Configuration
Click settings icon on any wallet to:
- Enable/Disable wallet
- Set trading side (UP/DOWN)
- Configure order amount ($1-$100)
- View wallet address

### 4. Trade History
- Real-time trade feed
- Market question
- Side (UP/DOWN)
- Amount and price
- Transaction status
- Timestamp

## Integration with Trading Bot

### Automatic Integration

Add to your `updown_bot.py`:

```python
from dashboard.bot_integration import integrate_with_dashboard

# After creating bot instance
bot = CryptoUpDownBot()

# Enable dashboard
dashboard = integrate_with_dashboard(bot)

# Run bot normally
bot.run()
```

### Manual Integration

```python
from dashboard.bot_integration import DashboardIntegration

# Create integration
dashboard = DashboardIntegration(
    api_url="http://localhost:5000/api",
    user_id="USER_12345"
)

# Report trades
await dashboard.report_trade({
    'wallet_number': 1,
    'market_id': 'market_id',
    'market_question': 'Will BTC reach $100k?',
    'side': 'UP',
    'amount': 10.0,
    'price': 0.65,
    'status': 'filled',
    'tx_hash': '0x...'
})

# Update wallet status
await dashboard.update_wallet_status(1, {
    'is_active': True,
    'balance': 1000.0,
    'position_count': 5,
    'daily_volume': 500.0,
    'pnl': 50.0
})
```

## API Endpoints

### REST API

- `GET /api/stats` - Get overall statistics
- `GET /api/wallets` - List all wallets
- `POST /api/wallets/{id}/config` - Update wallet configuration
- `GET /api/trades` - Get trade history
- `POST /api/trades` - Report new trade
- `POST /api/users/register` - Register new user

### WebSocket

- `ws://localhost:5000/ws?user_id=USER_12345` - Real-time updates

Message types:
```json
{
  "type": "trade",
  "data": { /* trade data */ }
}

{
  "type": "stats_update",
  "data": { /* statistics */ }
}

{
  "type": "wallet_update",
  "data": { /* wallet status */ }
}
```

## Configuration Files

### docker-compose.yml
- Frontend on port 80
- Backend API on port 5000
- Redis on port 6379
- Persistent volumes for data

### nginx.conf
- Reverse proxy configuration
- Static file caching
- WebSocket proxy support
- Security headers

### Requirements
- FastAPI backend framework
- Telegram bot library
- WebSocket support
- Database ORM
- Redis for caching

## Security

### Credential Protection
- Private keys encrypted with Fernet
- Auto-deletion of sensitive Telegram messages
- Environment variables for secrets
- HTTPS support (configure in nginx.conf)

### Best Practices
1. Use strong encryption key (32 bytes)
2. Enable HTTPS in production
3. Restrict API access with authentication
4. Regular backup of database
5. Monitor logs for suspicious activity

## Troubleshooting

### Common Issues

**Dashboard not loading**
```bash
# Check if services are running
docker-compose ps

# Check nginx logs
docker-compose logs nginx

# Verify ports are not in use
lsof -i :80
lsof -i :5000
```

**Telegram bot not responding**
```bash
# Check bot token in .env
grep TELEGRAM_BOT_TOKEN .env

# Check backend logs
docker-compose logs backend

# Test bot manually
python dashboard/telegram_bot.py
```

**WebSocket disconnecting**
```bash
# Check CORS settings
# Verify API_BASE_URL matches actual URL
# Check browser console for errors
```

**Database issues**
```bash
# Reset database
rm dashboard.db
docker-compose restart backend

# Check permissions
ls -la dashboard.db
```

## Development

### Local Development

```bash
# Backend development
cd dashboard/backend
pip install -r requirements.txt
uvicorn app:app --reload

# Frontend development
cd dashboard
python -m http.server 8080

# Telegram bot testing
python dashboard/telegram_bot.py
```

### Adding Features

1. **New API Endpoint**: Edit `backend/app.py`
2. **Frontend Updates**: Modify `index.html` and `dashboard.js`
3. **New Charts**: Add Chart.js configuration in `dashboard.js`
4. **Database Changes**: Update SQLAlchemy models in `app.py`

## Production Deployment

### 1. SSL Certificate

Uncomment HTTPS section in `nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ...
}
```

### 2. Environment Variables

Set production values in `.env`:

```env
FRONTEND_URL=https://yourdomain.com
API_BASE_URL=https://yourdomain.com/api
DATABASE_URL=postgresql://user:pass@db/dashboard
SECRET_KEY=strong_random_key_here
```

### 3. Scaling

```yaml
# docker-compose.override.yml
services:
  backend:
    deploy:
      replicas: 3
```

### 4. Monitoring

- Use Prometheus metrics endpoint: `/metrics`
- Configure alerts for high error rates
- Monitor WebSocket connection count
- Track API response times

## Support

For issues or questions:

1. Check logs: `docker-compose logs -f`
2. Review configuration files
3. Verify network connectivity
4. Check GitHub issues for similar problems

## License

This dashboard is part of the Polymarket Trading Bot system.

---

Created for monitoring and controlling Polymarket automated trading strategies.