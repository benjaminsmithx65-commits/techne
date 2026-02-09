# Techne VPS Deployment Script
# VPS: 149.28.236.151 (Vultr - Ubuntu 22.04)

$VPS_IP = "149.28.236.151"
$VPS_USER = "root"
$REMOTE_DIR = "/opt/techne"

Write-Host "=== Techne VPS Deployment ===" -ForegroundColor Cyan

# Step 1: Test SSH connection
Write-Host "`n[1/5] Testing SSH connection..." -ForegroundColor Yellow
Write-Host "You will need to enter password: fC}3HH7%8U4i@)A$" -ForegroundColor Magenta

# Step 2: Clean up VPS
Write-Host "`n[2/5] Cleaning up VPS..." -ForegroundColor Yellow
$cleanupCommands = @"
pm2 stop all 2>/dev/null
pm2 delete all 2>/dev/null
docker stop \$(docker ps -q) 2>/dev/null
docker rm \$(docker ps -aq) 2>/dev/null
rm -rf /opt/techne /opt/techne-finance /opt/techne-artisan
mkdir -p /opt/techne
echo 'Cleanup complete!'
"@

# Step 3: Install dependencies on VPS
Write-Host "`n[3/5] Installing dependencies..." -ForegroundColor Yellow
$installCommands = @"
apt-get update -qq
apt-get install -y python3-pip python3-venv docker.io docker-compose git curl
systemctl enable docker
systemctl start docker
echo 'Dependencies installed!'
"@

# Step 4: Copy files
Write-Host "`n[4/5] Copy files to VPS using SCP..." -ForegroundColor Yellow
Write-Host "Run these commands manually:" -ForegroundColor Green
Write-Host "scp -r backend ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"
Write-Host "scp docker-compose.yml ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"
Write-Host "scp Dockerfile.* ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"
Write-Host "scp .env ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/"

# Step 5: Start services
Write-Host "`n[5/5] Start services..." -ForegroundColor Yellow
$startCommands = @"
cd /opt/techne
docker-compose up -d --build
docker-compose ps
echo 'Deployment complete!'
"@

Write-Host "`n=== Manual SSH Commands ===" -ForegroundColor Cyan
Write-Host "ssh ${VPS_USER}@${VPS_IP}" -ForegroundColor White
Write-Host ""
Write-Host "# Then run:" -ForegroundColor Gray
Write-Host $cleanupCommands -ForegroundColor White
Write-Host ""
Write-Host $installCommands -ForegroundColor White
Write-Host ""
Write-Host $startCommands -ForegroundColor White
