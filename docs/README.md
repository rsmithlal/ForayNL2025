# ForayNL2025 Django Application Documentation

## Overview

The ForayNL2025 Django application is a fungal taxonomy matching system designed to help mycologists validate and review matches between Foray field collection data and MycoBank taxonomic records. The application provides a web interface for browsing, reviewing, and validating fungal species identifications.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django 4.0+
- SQLite (development) / PostgreSQL (production recommended)

### Installation
```bash
cd FORAY_DJANGO
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Initial Data Load
```bash
python manage.py load_full_pipeline
```

## 📁 Documentation Structure

### Core Documentation
- **[Architecture Overview](architecture/README.md)** - System design and data models
- **[Security Guide](security/README.md)** - Security analysis and hardening steps
- **[Deployment Guide](deployment/README.md)** - Production deployment instructions
- **[Development Guide](development/README.md)** - Local development setup and testing
- **[API Reference](api/README.md)** - API endpoints and integration guides

### Quick Reference
- **[Model Relationships](architecture/models.md)** - Database schema and relationships
- **[Security Checklist](security/checklist.md)** - Pre-deployment security verification
- **[Environment Configuration](deployment/environment.md)** - Settings and environment variables
- **[Testing Guide](development/testing.md)** - Test setup and best practices

## 🎯 Application Purpose

The ForayNL2025 application addresses the challenge of taxonomic validation in mycological research:

1. **Data Import**: Processes CSV files containing foray collection data
2. **Automated Matching**: Runs algorithms to match foray specimens with MycoBank records
3. **Review Interface**: Provides web UI for expert review of matches and mismatches
4. **Validation Workflow**: Enables mycologists to validate, correct, or flag taxonomic identifications
5. **Data Export**: Exports reviewed and validated data for research use

## 🏗️ System Components

### Django Application (`FORAY_DJANGO/`)
- **Core App**: Main business logic and models
- **Management Commands**: Data pipeline automation
- **Web Interface**: Review and validation UI
- **Admin Interface**: Administrative functions

### Integration Components
- **FastAPI Server**: Handles Google Drive push notifications
- **Data Pipeline**: Automated processing scripts
- **CSV Processing**: Import/export functionality

## 📊 Key Features

### Match Categorization
- **Perfect Matches**: Exact taxonomic matches between foray and MycoBank data
- **Mismatches**: Records requiring review with similarity scores
- **All Matches**: Complete matching results with confidence levels

### Review Workflow
- **Dashboard**: Overview of match categories and statistics
- **Detail Views**: Individual record examination
- **Validation Forms**: Expert review and correction interface
- **Export Functions**: CSV export of reviewed data

### Data Management
- **Bulk Import**: Process large foray datasets
- **Automated Pipeline**: Background processing of new data
- **Version Control**: Track changes and reviewer information

## 🔧 Current Status

### ✅ Strengths
- Well-structured Django application following best practices
- Clear separation of concerns and modular design
- Comprehensive data models covering the complete workflow
- User-friendly interface for taxonomic review
- Automated pipeline integration capabilities

### ⚠️ Areas Requiring Attention
- **Security Configuration**: Hardcoded secrets and debug settings
- **Input Validation**: Limited sanitization of user inputs
- **Error Handling**: Basic error management needs enhancement
- **Testing Coverage**: No comprehensive test suite
- **Production Configuration**: Development settings need production hardening

## 📋 Pre-Production Checklist

Before deploying to production, review these critical areas:

1. **🔴 Security (CRITICAL)**
   - [ ] Configure environment-based secret key
   - [ ] Disable debug mode in production
   - [ ] Set proper ALLOWED_HOSTS
   - [ ] Implement HTTPS and security headers

2. **⚠️ Configuration (HIGH PRIORITY)**
   - [ ] Set up production database (PostgreSQL recommended)
   - [ ] Configure logging and error monitoring
   - [ ] Implement proper input validation
   - [ ] Set up static file serving

3. **📋 Testing & Quality (MEDIUM PRIORITY)**
   - [ ] Implement comprehensive test suite
   - [ ] Set up continuous integration
   - [ ] Performance testing and optimization
   - [ ] Code quality checks

## 🤝 Contributing

For development guidelines and contribution instructions, see:
- [Development Setup](development/setup.md)
- [Testing Guidelines](development/testing.md)
- [Code Style Guide](development/style-guide.md)

## 📞 Support

For questions or issues:
1. Check the relevant documentation sections
2. Review the [troubleshooting guide](development/troubleshooting.md)
3. Contact the development team

---

**Next Steps**: Review the [Security Guide](security/README.md) for immediate security improvements before any production deployment.