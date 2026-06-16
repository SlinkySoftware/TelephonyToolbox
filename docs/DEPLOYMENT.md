# Telephony Toolbox Deployment Guide

Complete production deployment on RHEL 9 with nginx, Gunicorn, PostgreSQL, and systemd.

## Table of Contents

1. [Deployment Architecture](#deployment-architecture)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [SSL/TLS Setup](#ssltls-setup)
7. [SELinux Configuration](#selinux-configuration)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Upgrades](#upgrades)

---

## Deployment Architecture

```
Client Browser (HTTPS)
       ↓
    nginx (port 443)
    ├─ /static/*  → /var/www/telephonytoolbox/dist/spa/ (Quasar SPA)
    └─ /api/*     → proxy_pass 127.0.0.1:8010 (Gunicorn)
       ↓
Gunicorn (127.0.0.1:8010)
       ├─ 4 worker processes
       └─ Manages Django application
       ↓
PostgreSQL (localhost:5432)
       ├─ telephonytoolbox database
       └─ Session and audit data
       ↓
External Services
       ├─ CUCM AXL (Cisco UCM)
       ├─ LDAP Server (identity provider)
       └─ Entra (Microsoft authentication)
```

### Directory Structure

```
/opt/telephonytoolbox/              # Application root
  ├─ .git/                          # Git repository
  ├─ .env                           # Symlink: /etc/telephonytoolbox/backend.env
  ├─ backend/                       # Django application
  │  ├─ manage.py
  │  ├─ requirements.txt
  │  └─ ... (apps, migrations)
  ├─ frontend/                      # Quasar frontend
  │  ├─ dist/spa/                   # Built SPA files (nginx serves)
  │  └─ ... (src, node_modules)
  ├─ scripts/                       # Deployment scripts
  └─ docs/                          # Documentation

/var/www/telephonytoolbox/          # Web root (nginx)
  └─ dist/spa/                      # Symlink to frontend/dist/spa/

/etc/telephonytoolbox/              # Configuration
  ├─ backend.env                    # Environment file
  └─ nginx.conf                     # nginx site config (symlink to /etc/nginx/sites-available/)

/var/log/telephonytoolbox/          # Application logs
  ├─ application.log                # Django application logs
  ├─ gunicorn-access.log            # Gunicorn access logs
  ├─ nginx-access.log               # nginx access logs (optional)
  └─ nginx-error.log                # nginx error logs (optional)

/run/telephonytoolbox/              # Runtime files
  └─ gunicorn.sock                  # Gunicorn socket (systemd managed)
```

---

## Prerequisites

### System Requirements

- **OS**: RHEL 9 (or CentOS 9 compatible)
- **RAM**: 2+ GB
- **Storage**: 20+ GB
- **CPU**: 2+ cores recommended

### Required Packages

```bash
sudo yum install -y \
  git \
  python3 python3-venv python3-devel \
  postgresql postgresql-devel \
  nginx \
  gcc \
  openssl-devel libffi-devel

# Optional but recommended
sudo yum install -y \
  vim \
  curl \
  htop \
  logrotate
```

### Firewall Rules

```bash
# Allow HTTP/HTTPS
sudo firewall-cmd --permanent --add-service http
sudo firewall-cmd --permanent --add-service https

# Allow PostgreSQL (if remote)
# sudo firewall-cmd --permanent --add-port 5432/tcp

sudo firewall-cmd --reload
```

---

## Installation Steps

### Step 1: Create Application User

```bash
# Create dedicated user (no login shell)
sudo useradd -r -s /bin/false -d /opt/telephonytoolbox telephonytoolbox

# Verify
id telephonytoolbox
# uid=998(telephonytoolbox) gid=997(telephonytoolbox) groups=997(telephonytoolbox)
```

### Step 2: Create Directory Structure

```bash
# Create directories
sudo mkdir -p /opt/telephonytoolbox
sudo mkdir -p /var/www/telephonytoolbox
sudo mkdir -p /etc/telephonytoolbox
sudo mkdir -p /var/log/telephonytoolbox
sudo mkdir -p /run/telephonytoolbox

# Set ownership
sudo chown telephonytoolbox:telephonytoolbox /opt/telephonytoolbox
sudo chown telephonytoolbox:telephonytoolbox /var/www/telephonytoolbox
sudo chown telephonytoolbox:telephonytoolbox /var/log/telephonytoolbox
sudo chown telephonytoolbox:telephonytoolbox /run/telephonytoolbox

# Set permissions
sudo chmod 755 /opt/telephonytoolbox
sudo chmod 755 /var/www/telephonytoolbox
sudo chmod 755 /var/log/telephonytoolbox
sudo chmod 755 /run/telephonytoolbox
```

### Step 3: Clone Repository

```bash
# As root or with sudo
cd /opt/telephonytoolbox
sudo git clone https://github.com/SlinkySoftware/TelephonyToolbox.git .

# Or if you have a specific branch/version
sudo git clone -b main https://github.com/SlinkySoftware/TelephonyToolbox.git .

# Set ownership
sudo chown -R telephonytoolbox:telephonytoolbox /opt/telephonytoolbox/.git
```

### Step 4: Setup Python Virtual Environment

```bash
cd /opt/telephonytoolbox

# As root or sudo
sudo -u telephonytoolbox python3 -m venv venv

# Activate and install
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && pip install -U pip'
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && pip install -r backend/requirements.txt'
```

### Step 5: Setup PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres createuser -P telephonytoolbox
# (Set password when prompted)

sudo -u postgres createdb -O telephonytoolbox telephonytoolbox

# Verify connection (as postgres user)
sudo -u postgres psql -U telephonytoolbox telephonytoolbox
# (Should connect; type \q to exit)
```

### Step 6: Configure Environment

```bash
# Create environment file
sudo cp scripts/env.example /etc/telephonytoolbox/backend.env

# Edit with production values
sudo vim /etc/telephonytoolbox/backend.env

# Key settings:
# - DJANGO_SECRET_KEY=<random-key>
# - DJANGO_ALLOWED_HOSTS=telephonytoolbox.example.internal
# - DATABASE_HOST=127.0.0.1
# - DATABASE_NAME=telephonytoolbox
# - DATABASE_USER=telephonytoolbox
# - DATABASE_PASSWORD=<from-above>
# - AUTH_MODE=entra (or ldap)
# - ENTRA/LDAP settings
# - CUCM settings

# Set ownership and permissions
sudo chown telephonytoolbox:telephonytoolbox /etc/telephonytoolbox/backend.env
sudo chmod 600 /etc/telephonytoolbox/backend.env  # Only app user can read

# Symlink to app directory
sudo ln -s /etc/telephonytoolbox/backend.env /opt/telephonytoolbox/.env
```

### Step 7: Build Frontend

```bash
cd /opt/telephonytoolbox

# Install frontend deps
sudo -u telephonytoolbox npm --prefix frontend ci

# Build SPA
sudo -u telephonytoolbox npm --prefix frontend run build

# Symlink to web root
sudo ln -s /opt/telephonytoolbox/frontend/dist/spa /var/www/telephonytoolbox/dist
```

### Step 8: Run Migrations

```bash
cd /opt/telephonytoolbox

# Run migrations
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py migrate'

# Collect static files (if any Django static files)
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py collectstatic --noinput'

# Create bootstrap app admin (optional)
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py bootstrap_local_app_admin \
  --email admin@example.com \
  --display-name "App Admin" \
  --password "InitialPassword123!"'
```

### Step 9: Setup Gunicorn

Create systemd service file:

```bash
sudo tee /etc/systemd/system/telephonytoolbox.service > /dev/null << 'EOF'
[Unit]
Description=Telephony Toolbox Application
After=network.target postgresql.service

[Service]
Type=notify
User=telephonytoolbox
Group=telephonytoolbox
WorkingDirectory=/opt/telephonytoolbox

# Load environment
EnvironmentFile=/etc/telephonytoolbox/backend.env

# Python path
Environment="PYTHONUNBUFFERED=1"

# Start command
ExecStart=/opt/telephonytoolbox/venv/bin/gunicorn \
  --workers 4 \
  --worker-class=sync \
  --bind=127.0.0.1:8010 \
  --access-logfile=/var/log/telephonytoolbox/gunicorn-access.log \
  --error-logfile=/var/log/telephonytoolbox/gunicorn-error.log \
  --log-level info \
  --timeout 300 \
  telephony_toolbox.wsgi:application

# Restart policy
Restart=on-failure
RestartSec=5s

# Process management
KillMode=mixed
KillSignal=SIGTERM

# Security
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable service (starts on boot)
sudo systemctl enable telephonytoolbox

# Test start
sudo systemctl start telephonytoolbox
sudo systemctl status telephonytoolbox
```

**Verify**:
```bash
# Check Gunicorn is listening
sudo ss -tlnp | grep 8010
# Should show: LISTEN ... 127.0.0.1:8010 ... gunicorn

# Check logs
sudo journalctl -u telephonytoolbox -n 50 -f
```

### Step 10: Setup nginx

Create nginx site configuration:

```bash
sudo tee /etc/nginx/sites-available/telephonytoolbox.conf > /dev/null << 'EOF'
upstream gunicorn {
    server 127.0.0.1:8010;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name telephonytoolbox.example.internal;
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name telephonytoolbox.example.internal;

    # SSL certificates (see SSL Setup section)
    ssl_certificate /etc/telephonytoolbox/certs/telephonytoolbox.crt;
    ssl_certificate_key /etc/telephonytoolbox/certs/telephonytoolbox.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Access logs
    access_log /var/log/telephonytoolbox/nginx-access.log;
    error_log /var/log/telephonytoolbox/nginx-error.log;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/json;
    gzip_min_length 1000;

    # Static files (Quasar SPA)
    location /static/ {
        alias /var/www/telephonytoolbox/dist/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API proxy to Gunicorn
    location /api/ {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Root path → SPA index
    location / {
        root /var/www/telephonytoolbox/dist;
        try_files $uri /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Health check endpoint (no auth required)
    location /healthz {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/telephonytoolbox.conf \
  /etc/nginx/sites-enabled/telephonytoolbox.conf

# Test configuration
sudo nginx -t
# Should output: nginx: the configuration file .../nginx.conf syntax is ok

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl status nginx
```

---

## SSL/TLS Setup

### Option 1: Let's Encrypt (Recommended for Public Domains)

```bash
# Install certbot
sudo yum install -y certbot python3-certbot-nginx

# Get certificate (interactive)
sudo certbot certonly --nginx -d telephonytoolbox.example.internal

# Verify certificate
sudo certbot certificates

# Update nginx.conf paths (will be done automatically by certbot)
# Typically: /etc/letsencrypt/live/telephonytoolbox.example.internal/

# Auto-renewal (already enabled)
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer
```

### Option 2: Self-Signed Certificate (Development/Internal)

```bash
# Create directory
sudo mkdir -p /etc/telephonytoolbox/certs

# Generate private key
sudo openssl genrsa -out /etc/telephonytoolbox/certs/telephonytoolbox.key 2048

# Generate certificate (valid 365 days)
sudo openssl req -new -x509 -key /etc/telephonytoolbox/certs/telephonytoolbox.key \
  -out /etc/telephonytoolbox/certs/telephonytoolbox.crt \
  -days 365 \
  -subj "/C=AU/ST=NSW/L=Sydney/O=Company/CN=telephonytoolbox.example.internal"

# Set permissions
sudo chmod 600 /etc/telephonytoolbox/certs/telephonytoolbox.key
sudo chmod 644 /etc/telephonytoolbox/certs/telephonytoolbox.crt

# Update nginx.conf to point to these paths (already done above)
```

### Option 3: Company CA Certificate

```bash
# Copy certificate and key from your CA
sudo cp /path/to/cert.crt /etc/telephonytoolbox/certs/telephonytoolbox.crt
sudo cp /path/to/key.key /etc/telephonytoolbox/certs/telephonytoolbox.key

# Set permissions
sudo chmod 600 /etc/telephonytoolbox/certs/telephonytoolbox.key
sudo chmod 644 /etc/telephonytoolbox/certs/telephonytoolbox.crt
```

### Verify SSL

```bash
# Test certificate
sudo openssl x509 -in /etc/telephonytoolbox/certs/telephonytoolbox.crt -text -noout

# Test HTTPS connection
curl -k https://localhost/
# (k = ignore self-signed cert warning)

# Check from external host
curl https://telephonytoolbox.example.internal
```

---

## SELinux Configuration

If SELinux is enabled (`getenforce` shows `Enforcing`):

```bash
# Set context for application directory
sudo chcon -R -t usr_t /opt/telephonytoolbox

# Set context for web root
sudo chcon -R -t httpd_sys_content_t /var/www/telephonytoolbox

# Set context for log directory
sudo chcon -R -t httpd_log_t /var/log/telephonytoolbox

# Allow nginx to proxy to Gunicorn
sudo setsebool -P httpd_can_network_connect on

# Verify contexts
ls -Z /opt/telephonytoolbox
ls -Z /var/www/telephonytoolbox
ls -Z /var/log/telephonytoolbox

# Check booleans
getsebool httpd_can_network_connect
```

**If SELinux blocks something**:

```bash
# Check audit log
sudo grep telephonytoolbox /var/log/audit/audit.log

# Generate policy module
sudo audit2allow -a -M telephonytoolbox

# Install module
sudo semodule -i telephonytoolbox.pp
```

---

## Monitoring & Logs

### Application Logs

```bash
# Real-time logs
sudo journalctl -u telephonytoolbox -f

# Last 100 lines
sudo journalctl -u telephonytoolbox -n 100

# Yesterday's logs
sudo journalctl -u telephonytoolbox --since "yesterday"

# Application log file
sudo tail -f /var/log/telephonytoolbox/application.log
```

### nginx Logs

```bash
# Access logs
sudo tail -f /var/log/telephonytoolbox/nginx-access.log

# Error logs
sudo tail -f /var/log/telephonytoolbox/nginx-error.log
```

### System Status

```bash
# Service status
sudo systemctl status telephonytoolbox

# Process list
ps aux | grep gunicorn

# Port binding
sudo ss -tlnp | grep -E ":(80|443|8010)"

# Disk usage
df -h /opt /var /var/log

# Database size
sudo -u postgres psql telephonytoolbox -c "SELECT pg_size_pretty(pg_database_size('telephonytoolbox'));"
```

### Health Checks

```bash
# Basic health (no auth required)
curl https://telephonytoolbox.example.internal/healthz

# Admin health (requires auth)
curl -H "Cookie: sessionid=..." https://telephonytoolbox.example.internal/api/admin/health/

# Database connectivity
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py dbshell -c "SELECT 1"'
```

### Automatic Log Rotation

Create `/etc/logrotate.d/telephonytoolbox`:

```bash
sudo tee /etc/logrotate.d/telephonytoolbox > /dev/null << 'EOF'
/var/log/telephonytoolbox/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 telephonytoolbox telephonytoolbox
    sharedscripts
    postrotate
        /bin/systemctl reload nginx 2>/dev/null || true
    endscript
}
EOF

# Test configuration
sudo logrotate -v /etc/logrotate.d/telephonytoolbox
```

---

## Troubleshooting

### Application won't start

```bash
# Check service status
sudo systemctl status telephonytoolbox

# Check error logs
sudo journalctl -u telephonytoolbox -n 50

# Test migrations
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py migrate --dry-run'

# Test Django settings
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py check'
```

### Database connection error

```bash
# Check PostgreSQL running
sudo systemctl status postgresql

# Test connection
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py dbshell'

# Verify credentials in .env
sudo cat /etc/telephonytoolbox/backend.env | grep DATABASE_

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### CUCM connection fails

```bash
# Test CUCM connectivity
curl -k https://cucm.example.internal:8443/

# Verify credentials
cat /etc/telephonytoolbox/backend.env | grep CUCM_

# Check application logs for AXL errors
sudo journalctl -u telephonytoolbox | grep -i cucm
```

### LDAP authentication fails

```bash
# Test LDAP connectivity
ldapsearch -H ldaps://ldap.example.internal:636 \
  -D "cn=ldap-service,cn=users,dc=company,dc=internal" \
  -w "password" \
  -b "cn=users,dc=company,dc=internal" \
  "mail=user@company.com"

# Check LDAP configuration
cat /etc/telephonytoolbox/backend.env | grep LDAP_
```

### nginx returns 502 Bad Gateway

```bash
# Check Gunicorn listening
sudo ss -tlnp | grep 8010

# Check Gunicorn logs
sudo journalctl -u telephonytoolbox | tail

# Test proxy connection
curl http://127.0.0.1:8010/healthz

# Check nginx error log
sudo tail -f /var/log/telephonytoolbox/nginx-error.log
```

---

## Upgrades

### Backend Update

```bash
# Pull latest code
cd /opt/telephonytoolbox
sudo git pull origin main

# Install new dependencies (if any)
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  pip install -r backend/requirements.txt'

# Run migrations
sudo -u telephonytoolbox bash -c 'source venv/bin/activate && \
  python backend/manage.py migrate'

# Restart application
sudo systemctl restart telephonytoolbox

# Verify
sudo systemctl status telephonytoolbox
```

### Frontend Update

```bash
# Build new frontend
cd /opt/telephonytoolbox
sudo -u telephonytoolbox npm --prefix frontend ci
sudo -u telephonytoolbox npm --prefix frontend run build

# Symlink already points to dist/, so no extra steps needed
# Verify
curl https://telephonytoolbox.example.internal/

# Reload nginx cache (optional)
sudo systemctl reload nginx
```

### Rollback

```bash
# If update breaks things:
cd /opt/telephonytoolbox

# Checkout previous version
sudo git checkout HEAD~1

# Rebuild frontend (if needed)
sudo -u telephonytoolbox npm --prefix frontend ci
sudo -u telephonytoolbox npm --prefix frontend run build

# Restart
sudo systemctl restart telephonytoolbox

# Run migrations backwards (if needed)
# Note: Django doesn't auto-rollback; manual intervention may be needed
```

---

## Backup & Recovery

### Database Backup

```bash
# Full backup
sudo -u postgres pg_dump telephonytoolbox > /backup/telephonytoolbox_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
sudo -u postgres pg_dump -Fc telephonytoolbox > /backup/telephonytoolbox_$(date +%Y%m%d_%H%M%S).dump

# Automated daily backup
echo '0 2 * * * postgres pg_dump -Fc telephonytoolbox > /backup/telephonytoolbox_$(date +\%Y\%m\%d).dump' | \
  sudo tee -a /etc/crontab
```

### Database Restore

```bash
# From SQL dump
sudo -u postgres psql telephonytoolbox < /backup/telephonytoolbox_20260615.sql

# From Fc dump
sudo -u postgres pg_restore -d telephonytoolbox /backup/telephonytoolbox_20260615.dump
```

---

## Performance Tuning

### PostgreSQL

```bash
# Edit /etc/postgresql/15/main/postgresql.conf
# Common tuning (for 2GB system):

shared_buffers = 512MB           # 25% of RAM
effective_cache_size = 1536MB    # 75% of RAM
maintenance_work_mem = 128MB
work_mem = 8MB
random_page_cost = 1.1
```

### Gunicorn

In systemd service file, adjust worker count based on CPU cores:

```
# For 2 CPUs: 2-4 workers
# For 4 CPUs: 4-8 workers
# Formula: (2 x CPU cores) + 1
--workers 5
```

### nginx

Adjust connection limits in nginx.conf:

```
worker_processes auto;  # Match CPU count
worker_connections 1024;  # Connections per worker
```

---

## Security Hardening

### Firewall

```bash
# Restrict to specific IPs (if possible)
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" port protocol="tcp" port="443" accept'
sudo firewall-cmd --reload
```

### SSH Key-Based Auth

```bash
# Disable password authentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Fail2Ban

```bash
# Install
sudo yum install -y fail2ban

# Enable for nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
# Edit: enabled = true for nginx-http-auth

# Start
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Summary Checklist

- [ ] System updated: `sudo yum update -y`
- [ ] Packages installed
- [ ] Application user created
- [ ] Directories created with correct ownership
- [ ] Repository cloned
- [ ] Python venv created and dependencies installed
- [ ] PostgreSQL configured and database created
- [ ] Environment file configured
- [ ] Frontend built
- [ ] Migrations run
- [ ] Gunicorn service created and running
- [ ] nginx configured and running
- [ ] SSL certificates configured
- [ ] SELinux policies applied (if enabled)
- [ ] Log rotation configured
- [ ] Firewall rules configured
- [ ] Health checks passing
- [ ] Audit logs functional

**Post-Deployment Verification**:

```bash
# Access application
https://telephonytoolbox.example.internal

# Try login (use local account if configured)
# Check admin dashboard
# Check audit logs
# Review application logs for any warnings
```
