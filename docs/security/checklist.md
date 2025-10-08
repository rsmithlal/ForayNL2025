# Security Checklist - Pre-Deployment Verification

## 🔴 CRITICAL (Must Fix Before ANY Deployment)

### Environment Configuration
- [ ] **SECRET_KEY**: Generated unique key, stored in environment variable
- [ ] **DEBUG**: Set to `False` for production environment  
- [ ] **ALLOWED_HOSTS**: Configured with actual production domain(s)
- [ ] **Database URL**: Production database configured (not SQLite)

### Basic Security Headers
- [ ] **HTTPS Enforcement**: `SECURE_SSL_REDIRECT = True`
- [ ] **HSTS Headers**: `SECURE_HSTS_SECONDS` configured
- [ ] **Content Security**: `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] **XSS Protection**: `SECURE_BROWSER_XSS_FILTER = True`

## ⚠️ HIGH PRIORITY (Fix Before Public Access)

### Input Validation
- [ ] **Form Validation**: All forms have proper validation rules
- [ ] **File Uploads**: File type and size restrictions implemented
- [ ] **SQL Injection**: Parameterized queries used throughout
- [ ] **XSS Prevention**: All user input properly escaped

### Session Security  
- [ ] **Secure Cookies**: `SESSION_COOKIE_SECURE = True`
- [ ] **HttpOnly Cookies**: `SESSION_COOKIE_HTTPONLY = True`
- [ ] **CSRF Protection**: `CSRF_COOKIE_SECURE = True`
- [ ] **Session Timeout**: Reasonable `SESSION_COOKIE_AGE` set

### Access Control
- [ ] **Admin Security**: Admin URLs changed from default
- [ ] **Authentication**: Strong password requirements
- [ ] **Authorization**: Proper permission checks on all views
- [ ] **API Access**: Rate limiting implemented if applicable

## 📋 MEDIUM PRIORITY (Address Within First Month)

### Monitoring & Logging
- [ ] **Security Logging**: Failed login attempts logged
- [ ] **Error Monitoring**: Production error tracking configured
- [ ] **Access Logs**: Web server access logging enabled
- [ ] **Audit Trail**: Important actions logged with user info

### Database Security
- [ ] **Connection Encryption**: SSL/TLS for database connections
- [ ] **Backup Security**: Encrypted backups with access controls
- [ ] **User Permissions**: Database users with minimal required permissions
- [ ] **Regular Updates**: Database software kept current

### Infrastructure
- [ ] **Server Hardening**: OS security updates current
- [ ] **Network Security**: Firewall rules configured
- [ ] **SSL Certificate**: Valid certificate from trusted CA
- [ ] **Security Headers**: Additional headers via web server config

## 🔧 LOW PRIORITY (Address Within First Quarter)

### Advanced Security
- [ ] **Content Security Policy**: CSP headers configured
- [ ] **Dependency Scanning**: Regular vulnerability scans
- [ ] **Penetration Testing**: Professional security assessment
- [ ] **Security Training**: Team security awareness training

### Operational Security
- [ ] **Incident Response**: Security incident response plan
- [ ] **Key Management**: Secure key rotation procedures
- [ ] **Backup Testing**: Regular backup restoration testing
- [ ] **Documentation**: Security procedures documented

## 🧪 Testing Checklist

### Automated Security Tests
```bash
# Run these tests before deployment
python manage.py check --deploy
python manage.py test tests.test_security
bandit -r . -f json -o security_report.json
safety check
```

### Manual Security Tests
- [ ] **Authentication Bypass**: Test login/logout functionality
- [ ] **Authorization**: Test access controls on all pages
- [ ] **Input Validation**: Test with malicious payloads
- [ ] **File Upload**: Test with various file types and sizes
- [ ] **Session Management**: Test session timeout and security

## 📝 Configuration Examples

### Minimal Secure Environment File
```bash
# .env (NEVER commit this file)
DJANGO_SECRET_KEY=your-unique-50-char-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/foray_db
DJANGO_LOG_LEVEL=WARNING
```

### Security Settings Verification
```python
# Add to settings.py for verification
if not DEBUG:
    # Verify critical security settings
    assert SECRET_KEY != 'dev-secret-key-change-me', "Change the SECRET_KEY!"
    assert ALLOWED_HOSTS, "ALLOWED_HOSTS must be configured for production"
    assert SECURE_SSL_REDIRECT, "HTTPS must be enforced in production"
```

## 🚨 Deployment Verification Commands

### Pre-Deployment Check
```bash
# Verify security settings
python manage.py check --deploy

# Test with production settings
DJANGO_DEBUG=False python manage.py runserver

# Verify SSL certificate (after deployment)
curl -I https://yourdomain.com

# Check security headers
curl -I https://yourdomain.com | grep -i "strict-transport\|x-frame\|x-content"
```

### Post-Deployment Verification
```bash
# Verify no debug info leaked
curl https://yourdomain.com/nonexistent-page

# Test HTTPS redirect
curl -I http://yourdomain.com

# Verify admin is not accessible at default URL
curl -I https://yourdomain.com/admin/
```

## 🔄 Regular Security Maintenance

### Weekly Tasks
- [ ] Review security logs for anomalies
- [ ] Check for failed login attempts
- [ ] Verify backup integrity
- [ ] Monitor error rates

### Monthly Tasks  
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Review and rotate API keys
- [ ] Check SSL certificate expiration
- [ ] Security scan with `bandit` and `safety`

### Quarterly Tasks
- [ ] Full security assessment
- [ ] Penetration testing (if applicable)
- [ ] Security policy review
- [ ] Incident response plan testing

## ⚡ Quick Security Status Check

Use this one-liner to quickly check critical security settings:

```bash
python -c "
from django.conf import settings
import django
django.setup()
print('SECRET_KEY set:', len(settings.SECRET_KEY) > 20)
print('DEBUG disabled:', not settings.DEBUG)
print('ALLOWED_HOSTS configured:', bool(settings.ALLOWED_HOSTS))
print('HTTPS enforced:', getattr(settings, 'SECURE_SSL_REDIRECT', False))
"
```

## 📞 Security Incident Contacts

In case of security issues:
1. **Immediate**: Disable affected systems
2. **Document**: Record all details and timeline  
3. **Assess**: Determine scope and impact
4. **Notify**: Inform stakeholders as appropriate
5. **Fix**: Implement and test fixes
6. **Monitor**: Enhanced monitoring post-incident

---

**Remember**: Security is an ongoing process, not a one-time checklist. Regular reviews and updates are essential for maintaining a secure application.