# Deployment Guide

## Production Deployment Overview

This guide covers deploying the ForayNL2025 Django application to a production environment with proper security, performance, and reliability configurations.

## 🔧 Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04 LTS or similar Linux distribution
- **Python**: 3.8 or higher
- **Database**: PostgreSQL 12+ (recommended) or SQLite for small deployments
- **Web Server**: nginx + gunicorn (recommended) or Apache + mod_wsgi
- **SSL Certificate**: Valid certificate from Let's Encrypt or commercial CA
- **Memory**: Minimum 1GB RAM, 2GB+ recommended
- **Storage**: 10GB+ available disk space

### Infrastructure Components

```mermaid
graph TB
    subgraph "External Access"
        INT[Internet Traffic]
        CDN[CDN/CloudFlare<br/>Static Assets & DDoS Protection]
    end
    
    subgraph "Load Balancing & SSL"
        LB[Load Balancer<br/>SSL Termination]
        SSL[SSL Certificate<br/>Let's Encrypt/Commercial]
    end
    
    subgraph "Web Server Layer"
        NGINX[nginx<br/>Reverse Proxy<br/>Static File Serving]
        STATIC[Static Files<br/>CSS, JS, Images]
    end
    
    subgraph "Application Layer"
        GUNICORN[Gunicorn<br/>WSGI Server<br/>Multiple Workers]
        DJANGO[Django Application<br/>ForayNL2025]
        VENV[Python Virtual Environment<br/>Dependencies & Packages]
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Primary Database<br/>Match & Review Data)]
        REDIS[(Redis<br/>Cache & Sessions<br/>Background Jobs)]
        BACKUP[(Backup Storage<br/>Automated Backups<br/>Point-in-Time Recovery)]
    end
    
    subgraph "External Services"
        GD[Google Drive<br/>Data Source<br/>CSV Files]
        FASTAPI[FastAPI Server<br/>Webhook Handler<br/>Separate Container]
        MONITOR[Monitoring<br/>Logs & Metrics<br/>Health Checks]
    end
    
    INT --> CDN
    CDN --> LB
    SSL --> LB
    LB --> NGINX
    
    NGINX --> STATIC
    NGINX --> GUNICORN
    
    GUNICORN --> DJANGO
    DJANGO --> VENV
    
    DJANGO --> POSTGRES
    DJANGO --> REDIS
    POSTGRES --> BACKUP
    
    GD -->|Webhooks| FASTAPI
    FASTAPI -->|Triggers| DJANGO
    DJANGO --> MONITOR
    
    style INT fill:#ffebee
    style NGINX fill:#e3f2fd
    style DJANGO fill:#f3e5f5
    style POSTGRES fill:#e8f5e8
    style FASTAPI fill:#fff3e0
```

## 📋 Pre-Deployment Checklist

### Security Verification
- [ ] Complete [Security Checklist](../security/checklist.md)
- [ ] Environment variables configured
- [ ] SECRET_KEY generated and secured
- [ ] DEBUG=False verified
- [ ] ALLOWED_HOSTS properly configured
- [ ] Database credentials secured

### Infrastructure Ready
- [ ] Production server provisioned
- [ ] Domain name configured
- [ ] SSL certificate obtained
- [ ] Database server configured
- [ ] Backup strategy implemented

## 🚀 Deployment Steps

### Step 1: Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib

# Create application user
sudo useradd -m -s /bin/bash foray
sudo usermod -aG sudo foray
```

### Step 2: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE foray_production;
CREATE USER foray_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE foray_production TO foray_user;
ALTER USER foray_user CREATEDB;
\q

# Configure PostgreSQL for production
sudo nano /etc/postgresql/12/main/postgresql.conf
# Uncomment and modify:
# listen_addresses = 'localhost'
# max_connections = 100
# shared_buffers = 256MB

sudo systemctl restart postgresql
```

### Step 3: Application Deployment

```bash
# Switch to application user
sudo -u foray -i

# Create application directory
mkdir -p /home/foray/foray-app
cd /home/foray/foray-app

# Clone repository (replace with actual repository)
git clone https://github.com/your-org/ForayNL2025.git .
cd FORAY_DJANGO

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-dotenv

# Create environment configuration
cat > .env << EOF
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://foray_user:secure_password_here@localhost:5432/foray_production
DJANGO_LOG_LEVEL=INFO
EOF

# Secure the environment file
chmod 600 .env
```

### Step 4: Django Application Configuration

```bash
# Run database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Load initial data
python manage.py load_full_pipeline

# Test the application
python manage.py check --deploy
```

### Step 5: Gunicorn Configuration

```bash
# Create gunicorn configuration
cat > /home/foray/foray-app/FORAY_DJANGO/gunicorn_config.py << EOF
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
user = "foray"
group = "foray"
raw_env = ["DJANGO_SETTINGS_MODULE=config.settings"]
pidfile = "/home/foray/foray-app/gunicorn.pid"
accesslog = "/home/foray/foray-app/logs/gunicorn_access.log"
errorlog = "/home/foray/foray-app/logs/gunicorn_error.log"
loglevel = "info"
EOF

# Create log directory
mkdir -p /home/foray/foray-app/logs

# Test gunicorn
source venv/bin/activate
gunicorn --config gunicorn_config.py config.wsgi:application
```

### Step 6: Systemd Service Configuration

```bash
# Create systemd service file
sudo cat > /etc/systemd/system/foray-django.service << EOF
[Unit]
Description=Foray Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=foray
Group=foray
WorkingDirectory=/home/foray/foray-app/FORAY_DJANGO
Environment="PATH=/home/foray/foray-app/FORAY_DJANGO/venv/bin"
ExecStart=/home/foray/foray-app/FORAY_DJANGO/venv/bin/gunicorn --config gunicorn_config.py config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable foray-django
sudo systemctl start foray-django
sudo systemctl status foray-django
```

### Step 7: nginx Configuration

```bash
# Create nginx configuration
sudo cat > /etc/nginx/sites-available/foray-django << EOF
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Static files
    location /static/ {
        alias /home/foray/foray-app/FORAY_DJANGO/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/foray/foray-app/FORAY_DJANGO/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Health check endpoint
    location /health/ {
        access_log off;
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/foray-django /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 📊 Environment Configuration

### Production Settings

```python
# config/settings.py modifications for production
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Security settings
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security middleware and settings
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware
]

# HTTPS and security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR.parent / 'logs' / 'django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Environment Variables Template

```bash
# Production environment template
DJANGO_SECRET_KEY=your-50-character-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/foray_production
DJANGO_LOG_LEVEL=INFO

# Email settings (if needed)
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# External service keys (if applicable)
SENTRY_DSN=https://your-sentry-dsn-here
```

## � Container Architecture

### Docker Deployment Overview

```mermaid
graph TB
    subgraph "Docker Host System"
        subgraph "Application Stack"
            subgraph "Web Layer"
                NGINX_C[nginx Container<br/>- Reverse Proxy<br/>- SSL Termination<br/>- Static File Serving]
            end
            
            subgraph "Application Layer" 
                DJANGO_C[Django Container<br/>- Gunicorn WSGI Server<br/>- Python Application<br/>- Business Logic]
                WORKER_C[Background Workers<br/>- Data Processing<br/>- Pipeline Tasks<br/>- Async Jobs]
            end
            
            subgraph "Data Layer"
                POSTGRES_C[(PostgreSQL Container<br/>- Primary Database<br/>- ACID Transactions<br/>- Full-text Search)]
                REDIS_C[(Redis Container<br/>- Session Storage<br/>- Caching Layer<br/>- Job Queue)]
            end
            
            subgraph "Integration Layer"
                FASTAPI_C[FastAPI Container<br/>- Webhook Handler<br/>- External API Gateway<br/>- Event Processing]
            end
        end
        
        subgraph "Infrastructure"
            VOLUMES[(Persistent Volumes<br/>- Database Data<br/>- Media Files<br/>- Log Files)]
            NETWORKS[Docker Networks<br/>- Internal Communication<br/>- Service Discovery]
            CONFIGS[Configuration<br/>- Environment Variables<br/>- Secrets Management]
        end
        
        subgraph "Monitoring"
            LOGS[Log Aggregation<br/>- Application Logs<br/>- Access Logs<br/>- Error Tracking]
            HEALTH[Health Checks<br/>- Service Status<br/>- Performance Metrics]
        end
    end
    
    subgraph "External Services"
        GD[Google Drive<br/>Data Source]
        BACKUP[External Backup<br/>Cloud Storage]
        CDN[CDN/CloudFlare<br/>Asset Delivery]
    end
    
    %% Container Connections
    NGINX_C --> DJANGO_C
    DJANGO_C --> POSTGRES_C
    DJANGO_C --> REDIS_C
    DJANGO_C --> WORKER_C
    
    FASTAPI_C --> DJANGO_C
    FASTAPI_C --> REDIS_C
    
    %% Infrastructure Connections
    POSTGRES_C --> VOLUMES
    DJANGO_C --> VOLUMES
    REDIS_C --> VOLUMES
    
    NGINX_C --> NETWORKS
    DJANGO_C --> NETWORKS
    POSTGRES_C --> NETWORKS
    REDIS_C --> NETWORKS
    FASTAPI_C --> NETWORKS
    
    DJANGO_C --> CONFIGS
    FASTAPI_C --> CONFIGS
    
    %% Monitoring Connections
    DJANGO_C --> LOGS
    NGINX_C --> LOGS
    FASTAPI_C --> LOGS
    
    DJANGO_C --> HEALTH
    POSTGRES_C --> HEALTH
    
    %% External Connections
    GD --> FASTAPI_C
    POSTGRES_C --> BACKUP
    NGINX_C --> CDN
    
    style NGINX_C fill:#e3f2fd
    style DJANGO_C fill:#f3e5f5
    style POSTGRES_C fill:#e8f5e8
    style FASTAPI_C fill:#fff3e0
    style VOLUMES fill:#f1f8e9
```

### Docker Compose Configuration

```mermaid
graph LR
    subgraph "docker-compose.yml Services"
        subgraph "Core Services"
            WEB[web<br/>nginx + static files<br/>Port: 80, 443]
            APP[app<br/>django + gunicorn<br/>Internal: 8000]
            DB[db<br/>postgresql<br/>Internal: 5432]
            CACHE[cache<br/>redis<br/>Internal: 6379]
        end
        
        subgraph "Integration Services"
            WEBHOOK[webhook<br/>fastapi server<br/>Port: 8080]
            WORKER[worker<br/>background tasks<br/>Celery/RQ]
        end
        
        subgraph "Support Services"
            MONITOR[monitoring<br/>log aggregation<br/>health checks]
        end
    end
    
    subgraph "Persistent Storage"
        DB_VOL[postgres_data<br/>Database files]
        STATIC_VOL[static_files<br/>CSS, JS, Images]
        MEDIA_VOL[media_files<br/>User uploads]
        LOG_VOL[log_files<br/>Application logs]
    end
    
    subgraph "Network Configuration"
        FRONTEND[frontend network<br/>public access]
        BACKEND[backend network<br/>internal services]
        DATABASE[database network<br/>data access only]
    end
    
    subgraph "Configuration Management"
        ENV[.env file<br/>environment variables]
        SECRETS[secrets.env<br/>sensitive data]
        CONFIG[config files<br/>nginx, gunicorn]
    end
    
    %% Service Dependencies
    WEB --> APP
    APP --> DB
    APP --> CACHE
    WEBHOOK --> APP
    WORKER --> DB
    WORKER --> CACHE
    
    %% Volume Mounts
    DB --> DB_VOL
    APP --> STATIC_VOL
    APP --> MEDIA_VOL
    WEB --> STATIC_VOL
    APP --> LOG_VOL
    
    %% Network Assignments
    WEB --> FRONTEND
    WEB --> BACKEND
    APP --> BACKEND
    DB --> DATABASE
    CACHE --> BACKEND
    WEBHOOK --> FRONTEND
    
    %% Configuration
    APP --> ENV
    DB --> ENV
    WEBHOOK --> ENV
    ENV --> SECRETS
    WEB --> CONFIG
    
    style WEB fill:#e3f2fd
    style APP fill:#f3e5f5
    style DB fill:#e8f5e8
    style WEBHOOK fill:#fff3e0
    style DB_VOL fill:#f1f8e9
```

### Container Communication Flow

```mermaid
sequenceDiagram
    participant Client as Web Browser
    participant Nginx as nginx Container
    participant Django as Django Container
    participant DB as PostgreSQL Container
    participant Redis as Redis Container
    participant FastAPI as FastAPI Container
    participant GDrive as Google Drive
    
    Note over Client, GDrive: Normal User Request Flow
    
    Client->>Nginx: HTTPS Request
    Nginx->>Nginx: SSL Termination<br/>Static File Check
    
    alt Static File Request
        Nginx-->>Client: Serve Static File
    else Dynamic Content
        Nginx->>Django: Proxy to Django
        Django->>Redis: Check Cache
        
        alt Cache Hit
            Redis-->>Django: Return Cached Data
        else Cache Miss
            Django->>DB: Database Query
            DB-->>Django: Return Data
            Django->>Redis: Store in Cache
        end
        
        Django-->>Nginx: HTTP Response
        Nginx-->>Client: HTTPS Response
    end
    
    Note over FastAPI, GDrive: Automated Processing Flow
    
    GDrive->>FastAPI: Webhook Notification
    FastAPI->>FastAPI: Validate Headers<br/>Process Event
    FastAPI->>Django: Trigger Management Command
    Django->>DB: Import/Process Data
    Django->>Redis: Update Cache Status
    DB-->>Django: Confirm Updates
    Django-->>FastAPI: Processing Complete
    FastAPI-->>GDrive: Acknowledge Webhook
```

## �🔄 Automated Deployment

### Deployment Script

```bash
#!/bin/bash
# deploy.sh - Automated deployment script

set -e

APP_DIR="/home/foray/foray-app"
DJANGO_DIR="$APP_DIR/FORAY_DJANGO"

echo "Starting deployment..."

# Backup current version
sudo -u foray cp -r $APP_DIR $APP_DIR.backup.$(date +%Y%m%d_%H%M%S)

# Pull latest code
cd $APP_DIR
sudo -u foray git pull origin main

# Activate virtual environment
cd $DJANGO_DIR
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart foray-django
sudo systemctl reload nginx

# Health check
sleep 5
if curl -f http://localhost:8000/health/; then
    echo "Deployment successful!"
else
    echo "Deployment failed - restoring backup"
    sudo systemctl stop foray-django
    sudo -u foray rm -rf $APP_DIR
    sudo -u foray mv $APP_DIR.backup.* $APP_DIR
    sudo systemctl start foray-django
    exit 1
fi

echo "Deployment completed successfully"
```

## 🔍 Monitoring and Health Checks

### Health Check Endpoint

```python
# Add to core/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Simple health check endpoint"""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
```

### Log Monitoring

```bash
# Monitor application logs
tail -f /home/foray/foray-app/logs/django.log
tail -f /home/foray/foray-app/logs/gunicorn_access.log
tail -f /home/foray/foray-app/logs/gunicorn_error.log

# Monitor nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### System Monitoring

```bash
# Monitor system resources
htop
df -h
free -h

# Monitor services
sudo systemctl status foray-django
sudo systemctl status nginx
sudo systemctl status postgresql
```

## 🔄 Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/home/foray/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/foray_backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

# Create database backup
sudo -u postgres pg_dump foray_production > $BACKUP_FILE

# Compress the backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "foray_backup_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: $BACKUP_FILE.gz"
```

### Application Backup

```bash
#!/bin/bash
# backup_application.sh

BACKUP_DIR="/home/foray/backups"
APP_DIR="/home/foray/foray-app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Create application backup (excluding logs and temporary files)
tar -czf $BACKUP_DIR/foray_app_$TIMESTAMP.tar.gz \
    --exclude='*.log' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    -C $(dirname $APP_DIR) $(basename $APP_DIR)

echo "Application backup completed: $BACKUP_DIR/foray_app_$TIMESTAMP.tar.gz"
```

### Recovery Procedure

```bash
# Database recovery
sudo -u postgres dropdb foray_production
sudo -u postgres createdb foray_production
sudo -u postgres psql foray_production < backup_file.sql

# Application recovery
sudo systemctl stop foray-django
cd /home/foray
tar -xzf backups/foray_app_TIMESTAMP.tar.gz
sudo systemctl start foray-django
```

## 📋 Post-Deployment Checklist

### Immediate Verification
- [ ] Application starts without errors
- [ ] Database connections work
- [ ] Static files serve correctly
- [ ] SSL certificate is valid
- [ ] All pages load properly
- [ ] Admin interface accessible

### Security Verification
- [ ] HTTPS redirect works
- [ ] Security headers present
- [ ] Debug mode disabled
- [ ] Error pages don't leak information
- [ ] File upload restrictions work

### Performance Testing
- [ ] Load testing completed
- [ ] Response times acceptable
- [ ] Memory usage monitored
- [ ] Database query performance verified

### Monitoring Setup
- [ ] Log rotation configured
- [ ] Health checks working
- [ ] Backup scripts scheduled
- [ ] Monitoring alerts configured

## 🚨 Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check service logs
   sudo journalctl -u foray-django -f
   
   # Check gunicorn logs
   tail -f /home/foray/foray-app/logs/gunicorn_error.log
   ```

2. **Database connection errors**
   ```bash
   # Test database connection
   sudo -u postgres psql foray_production
   
   # Check PostgreSQL logs
   sudo tail -f /var/log/postgresql/postgresql-12-main.log
   ```

3. **Static files not loading**
   ```bash
   # Recollect static files
   cd /home/foray/foray-app/FORAY_DJANGO
   source venv/bin/activate
   python manage.py collectstatic --noinput
   
   # Check nginx configuration
   sudo nginx -t
   ```

4. **SSL certificate issues**
   ```bash
   # Check certificate validity
   openssl x509 -in /path/to/certificate.crt -text -noout
   
   # Test SSL configuration
   curl -I https://yourdomain.com
   ```

### Emergency Procedures

1. **Application rollback**
   ```bash
   sudo systemctl stop foray-django
   sudo -u foray mv /home/foray/foray-app /home/foray/foray-app.broken
   sudo -u foray mv /home/foray/foray-app.backup.* /home/foray/foray-app
   sudo systemctl start foray-django
   ```

2. **Database rollback**
   ```bash
   sudo -u postgres dropdb foray_production
   sudo -u postgres createdb foray_production
   gunzip -c backup_file.sql.gz | sudo -u postgres psql foray_production
   ```

---

This deployment guide provides a comprehensive foundation for production deployment while maintaining security, performance, and reliability standards.