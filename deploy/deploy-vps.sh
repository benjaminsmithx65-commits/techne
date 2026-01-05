#!/bin/bash
# Techne Bot VPS Deployment Script
# Deploy to: Ubuntu VPS (DigitalOcean, Hetzner, etc.)

set -e

echo "🚀 Techne Bot VPS Setup"

# 1. System updates
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx

# 2. Create app directory
APP_DIR="/opt/techne"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# 3. Clone repo (or copy files)
cd $APP_DIR
# git clone <your-repo-url> .
# OR: scp -r ./backend user@vps:/opt/techne/

# 4. Python virtual env
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 5. Environment variables
cat > $APP_DIR/.env << 'EOF'
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-your_telegram_bot_token_here}
PYTHONUNBUFFERED=1
EOF

# 6. Systemd service for BOT
sudo tee /etc/systemd/system/techne-bot.service << EOF
[Unit]
Description=Techne Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment=TELEGRAM_BOT_TOKEN=8555503724:AAGUFGvYTKnQtXIKjqfLi0Sq04xcYP0BqNg
ExecStart=$APP_DIR/venv/bin/python run_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 7. Systemd service for BACKEND API
sudo tee /etc/systemd/system/techne-api.service << EOF
[Unit]
Description=Techne Finance API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 8. Start services
sudo systemctl daemon-reload
sudo systemctl enable techne-bot techne-api
sudo systemctl start techne-bot techne-api

echo "✅ Deployment complete!"
echo ""
echo "Commands:"
echo "  sudo systemctl status techne-bot"
echo "  sudo journalctl -u techne-bot -f"
echo "  sudo systemctl restart techne-bot"

# =====================================================
# OPTIONAL: Self-Hosted Nitter for X/Twitter Scraping
# =====================================================
# Nitter provides RSS feeds from X accounts without API costs
# This enables real-time scraping of @DefiLlama, @WalterBloomberg, etc.

setup_nitter() {
    echo ""
    echo "🐦 Setting up Nitter (X/Twitter Mirror)..."
    
    # Install Docker
    sudo apt install -y docker.io docker-compose
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker $USER
    
    # Create Nitter directory
    NITTER_DIR="/opt/nitter"
    sudo mkdir -p $NITTER_DIR
    sudo chown $USER:$USER $NITTER_DIR
    cd $NITTER_DIR
    
    # Download Nitter docker-compose
    cat > docker-compose.yml << 'NITTER_COMPOSE'
version: "3"
services:
  nitter:
    image: zedeus/nitter:latest
    container_name: nitter
    ports:
      - "8080:8080"
    volumes:
      - ./nitter.conf:/src/nitter.conf:ro
    depends_on:
      - nitter-redis
    restart: unless-stopped
    healthcheck:
      test: wget -nv --tries=1 --spider http://127.0.0.1:8080/DefiLlama || exit 1
      interval: 30s
      timeout: 5s
      retries: 2
  
  nitter-redis:
    image: redis:6-alpine
    container_name: nitter-redis
    command: redis-server --save 60 1 --loglevel warning
    volumes:
      - nitter-redis:/data
    restart: unless-stopped
    healthcheck:
      test: redis-cli ping
      interval: 30s
      timeout: 5s
      retries: 2

volumes:
  nitter-redis:
NITTER_COMPOSE

    # Create Nitter config
    cat > nitter.conf << 'NITTER_CONF'
[Server]
hostname = "localhost"
port = 8080
https = false
httpMaxConnections = 100
staticDir = "./public"
title = "Techne Nitter"
address = "0.0.0.0"

[Cache]
listMinutes = 240
rssMinutes = 10
redisHost = "nitter-redis"
redisPort = 6379
redisMaxConnections = 30
redisConnections = 20

[Config]
hmacKey = "secretkey123changeme"
base64Media = false
enableRSS = true
enableDebug = false
proxy = ""
proxyAuth = ""
tokenCount = 10

[Preferences]
theme = "Nitter"
replaceTwitter = "localhost"
replaceYouTube = ""
replaceReddit = ""
replaceInstagram = ""
proxyVideos = true
hlsPlayback = false
infiniteScroll = false
NITTER_CONF

    # Start Nitter
    docker-compose up -d
    
    echo "✅ Nitter running at http://localhost:8080"
    echo ""
    echo "Test RSS feed:"
    echo "  curl http://localhost:8080/DefiLlama/rss"
    echo ""
    
    # Update Techne config to use local Nitter
    echo ""
    echo "📝 Update x_scraper.py to use localhost:"
    echo '  self._nitter_instances = ["http://localhost:8080"]'
}

# Uncomment to setup Nitter:
# setup_nitter

echo ""
echo "=================================="
echo "🐦 To enable X/Twitter scraping:"
echo "  1. Run: setup_nitter"
echo "  2. Or manually: docker-compose up -d in /opt/nitter"
echo "  3. Update x_scraper.py with localhost:8080"
echo "=================================="
