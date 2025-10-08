# Security Analysis and Hardening Guide

## 🔴 CRITICAL SECURITY ISSUES

### 1. Hardcoded Secret Key
**Issue**: The Django secret key is hardcoded in settings.py
```python
SECRET_KEY = 'dev-secret-key-change-me'  # NEVER do this in production!
```

**Impact**: 
- Compromises session security and CSRF protection
- Allows attackers to forge session cookies and bypass security measures

**Fix**: Use environment variables
```python
import os
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set")
```

### 2. Debug Mode Enabled
**Issue**: `DEBUG = True` in production exposes sensitive information
```python
DEBUG = True  # Exposes stack traces and settings to users
```

**Impact**:
- Reveals sensitive system information in error pages
- Exposes Django settings and environment details
- Shows detailed stack traces to attackers

**Fix**: Environment-based debug configuration
```python
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
```

### 3. No Host Restrictions
**Issue**: Empty `ALLOWED_HOSTS` allows HTTP Host header attacks
```python
ALLOWED_HOSTS = []  # Accepts any host header
```

**Impact**:
- Enables HTTP Host header injection attacks
- Allows DNS rebinding attacks
- Can be used for password reset poisoning

**Fix**: Restrict to specific domains
```python
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')
```

## ⚠️ HIGH PRIORITY SECURITY IMPROVEMENTS

### 4. Missing Security Middleware
**Issue**: No security headers or HTTPS enforcement

**Fix**: Add comprehensive security middleware
```python
# Add to MIDDLEWARE in settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Should be first
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Security settings
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

### 5. Input Validation Weaknesses
**Issue**: Limited validation in forms and views

**Current Risk Areas**:
- File upload handling without proper validation
- Form inputs not properly sanitized
- No protection against malicious file types

**Fix**: Implement comprehensive validation
```python
# In forms.py
from django.core.validators import RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_file_size(value):
    filesize = value.size
    if filesize > 10 * 1024 * 1024:  # 10MB limit
        raise ValidationError("File too large. Size should not exceed 10 MB.")

class ReviewForm(forms.ModelForm):
    validated_name = forms.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z\s\-\.()]+$',
                message='Name can only contain letters, spaces, hyphens, periods, and parentheses.'
            )
        ],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    reviewer_name = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z\s\-\.]+$',
                message='Reviewer name can only contain letters, spaces, hyphens, and periods.'
            )
        ]
    )
    
    file_upload = forms.FileField(
        validators=[
            FileExtensionValidator(allowed_extensions=['csv', 'txt']),
            validate_file_size,
        ],
        required=False
    )
```

### 6. Database Security
**Issue**: Using SQLite for production data

**Risks**:
- No user authentication or access control
- File-based database vulnerable to unauthorized access
- Limited concurrent user support
- No encryption at rest

**Fix**: Migrate to PostgreSQL with proper configuration
```python
# Production database configuration
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Database connection security
if not DEBUG:
    DATABASES['default'].update({
        'OPTIONS': {
            'sslmode': 'require',
        }
    })
```

## 📋 MEDIUM PRIORITY IMPROVEMENTS

### 7. Session Security
**Fix**: Enhance session configuration
```python
# Session security settings
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1 hour
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
```

### 8. Logging and Monitoring
**Fix**: Implement security-focused logging
```python
import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': 'SECURITY {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'formatter': 'security',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔧 Implementation Steps

### Step 1: Create Environment Configuration
```bash
# Create .env file (never commit this!)
cat > .env << EOF
DJANGO_SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/foray_db
DJANGO_LOG_LEVEL=INFO
EOF
```

### Step 2: Update Requirements
```bash
# Add to requirements.txt
python-dotenv==1.0.0
dj-database-url==2.1.0
psycopg2-binary==2.9.7  # For PostgreSQL
gunicorn==21.2.0  # For production server
```

### Step 3: Create Secure Settings File
```python
# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings - NEVER hardcode these!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set")

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if os.getenv('DJANGO_ALLOWED_HOSTS') else []

# ... rest of settings with security enhancements
```

### Step 4: Create Security Test
```python
# tests/test_security.py
from django.test import TestCase, override_settings
from django.conf import settings

class SecuritySettingsTest(TestCase):
    def test_secret_key_not_default(self):
        """Ensure SECRET_KEY is not the default development key"""
        self.assertNotEqual(settings.SECRET_KEY, 'dev-secret-key-change-me')
    
    @override_settings(DEBUG=False)
    def test_debug_disabled_in_production(self):
        """Ensure DEBUG is disabled in production"""
        self.assertFalse(settings.DEBUG)
    
    def test_allowed_hosts_configured(self):
        """Ensure ALLOWED_HOSTS is properly configured"""
        if not settings.DEBUG:
            self.assertNotEqual(settings.ALLOWED_HOSTS, [])
```

## 📊 Security Checklist

### Pre-Deployment Security Verification

- [ ] **Environment Variables**
  - [ ] SECRET_KEY generated and set via environment
  - [ ] DEBUG=False for production
  - [ ] ALLOWED_HOSTS configured with actual domains
  - [ ] Database credentials not hardcoded

- [ ] **HTTPS and Headers**
  - [ ] SSL certificate configured
  - [ ] SECURE_SSL_REDIRECT=True
  - [ ] Security headers enabled (HSTS, XSS protection, etc.)
  - [ ] Cookie security flags set

- [ ] **Input Validation**
  - [ ] Form validation implemented
  - [ ] File upload restrictions in place
  - [ ] SQL injection prevention verified
  - [ ] XSS protection enabled

- [ ] **Database Security**
  - [ ] Production database (PostgreSQL) configured
  - [ ] Database access credentials secured
  - [ ] Connection encryption enabled
  - [ ] Regular backup strategy implemented

- [ ] **Logging and Monitoring**
  - [ ] Security event logging configured
  - [ ] Error monitoring set up
  - [ ] Access logs reviewed regularly
  - [ ] Failed login attempt monitoring

- [ ] **Access Control**
  - [ ] Admin interface secured
  - [ ] User authentication working properly
  - [ ] Session management secure
  - [ ] CSRF protection enabled

## 🚨 Emergency Response

If a security breach is suspected:

1. **Immediate Actions**
   - Change all secret keys immediately
   - Revoke and regenerate API keys
   - Reset admin passwords
   - Check access logs for suspicious activity

2. **Assessment**
   - Identify compromised data
   - Determine attack vector
   - Document timeline of events
   - Assess impact on users

3. **Recovery**
   - Apply security patches
   - Restore from clean backups if necessary
   - Implement additional monitoring
   - Notify affected users if required

## 📚 Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [Django Security Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)