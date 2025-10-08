# Docker Setup for ForayNL Django Application

This document provides instructions for running the ForayNL Django application using Docker.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Build and start services:**
   ```bash
   docker compose up --build
   ```

3. **Run migrations:**
   ```bash
   docker compose run --rm web python manage.py migrate
   ```

4. **Create superuser (optional):**
   ```bash
   docker compose run --rm web python manage.py createsuperuser
   ```

5. **Access the application:**
   - Web interface: http://localhost:8000
   - Admin interface: http://localhost:8000/admin

## Testing

### Automated Setup Verification
Run the complete setup verification:
```bash
./verify_docker_setup.sh
```

This script will:
- Build Docker containers
- Start database and Redis services  
- Test database connectivity
- Run Django system checks
- Execute migrations
- Run the test suite
- Clean up afterwards

### Manual Testing
To run tests manually:
```bash
# Start services
docker compose up -d db redis

# Run test suite
docker compose run --rm test pytest

# Run specific tests
docker compose run --rm test pytest tests/test_basic_functionality.py

# Run with verbose output
docker compose run --rm test pytest -v

# Clean up
docker compose down
```

## Development Workflow

### Starting Development Environment
```bash
# Start all services in background
docker compose up -d

# View logs
docker compose logs -f web

# Stop services
docker compose down
```

### Django Management Commands
```bash
# Run any Django command
docker compose run --rm web python manage.py <command>

# Standard Django commands:
docker compose run --rm web python manage.py shell
docker compose run --rm web python manage.py collectstatic
docker compose run --rm web python manage.py check

# Custom data import commands:
# Import Foray fungi data (2023 ForayNL dataset)
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv

# Import MycoBank taxonomic data (complete reference database)
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv

# Clear existing data before import
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv --clear

# Dry run to preview import without changing database
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv --dry-run

# View comprehensive data statistics
docker compose run --rm web python manage.py data_stats
```

### Database Operations
```bash
# Create migrations
docker compose run --rm web python manage.py makemigrations

# Apply migrations
docker compose run --rm web python manage.py migrate

# Reset database (WARNING: destroys all data)
docker compose down -v
docker compose up -d db
docker compose run --rm web python manage.py migrate
```

### Data Import Workflow

The application supports importing large taxonomic datasets using Git LFS and custom Django management commands.

#### Prerequisites
1. **Git LFS Setup**: Ensure Git LFS is installed and CSV files are downloaded:
   ```bash
   # Install Git LFS (if not already installed)
   git lfs install
   
   # Download large CSV files
   git lfs pull
   
   # Verify files are downloaded (not pointer files)
   ls -la data/
   head -3 data/2023ForayNL_Fungi.csv
   ```

2. **CSV Data Files** (stored in `data/` directory):
   - `2023ForayNL_Fungi.csv`: ForayNL 2023 fungi observation data (~375KB, 983 records)
   - `MBList.csv`: MycoBank taxonomic reference database (~390MB, 537,509 records)

#### Import Process
```bash
# Step 1: Import Foray fungi observations
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv

# Step 2: Import MycoBank reference database (takes several minutes)
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv

# Step 3: Verify import success
docker compose run --rm web python manage.py data_stats
```

#### Advanced Import Options
```bash
# Preview import without making changes
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv --dry-run

# Clear existing data before import (fresh start)
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv --clear

# Import with progress tracking (automatically included)
# Shows real-time progress: "📈 Processed 100,000 records..."
```

#### Import Features
- **Batch Processing**: Memory-efficient import of large datasets (500K+ records)
- **Encoding Detection**: Automatic detection and handling of different character encodings (UTF-8, Latin-1, etc.)
- **Progress Tracking**: Real-time progress indicators with beautiful console output
- **Error Handling**: Graceful handling of malformed records with detailed error reporting
- **Transaction Safety**: Atomic database operations prevent partial imports
- **Data Quality Metrics**: Comprehensive statistics on import success rates
- **Resume Capability**: Duplicate detection allows safe re-running of imports

#### Expected Results
After successful import:
- **Foray Fungi**: ~983 observation records (100% coverage)
- **MycoBank List**: ~537,483 taxonomic reference records (99.995% coverage)  
- **Database Size**: ~183MB total
- **Data Quality**: Excellent coverage on taxonomic names, authors, and reference links

## Services

The Docker Compose setup includes:

- **web**: Django application server (port 8000)
- **db**: PostgreSQL database (port 5432)  
- **redis**: Redis cache/session store (port 6379)
- **test**: Test runner service (same as web but for testing)

### External Startup Scripts

The application includes enhanced startup scripts for better development workflow:

- **startup.sh**: Production-ready web application startup with data import detection
- **test-startup.sh**: Dedicated test environment startup script

These scripts provide:
- Beautiful console logging with emoji indicators
- Database connectivity verification
- Automatic migration execution  
- Static file collection
- Data import status detection
- Comprehensive error handling

## Environment Variables

Key environment variables (see `.env.example`):

- `SECRET_KEY`: Django secret key (required)
- `DEBUG`: Enable debug mode (default: True)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_*`: Database connection settings
- `REDIS_URL`: Redis connection URL

## Volumes

- `postgres_data`: PostgreSQL data persistence
- `redis_data`: Redis data persistence
- `.`: Application code (mounted for development)

## Ports

- `8000`: Django web application
- `5432`: PostgreSQL database
- `6379`: Redis cache

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Change port in docker-compose.yml if needed
   ```

2. **Database connection errors:**
   ```bash
   # Restart database service
   docker compose restart db
   
   # Check database logs
   docker compose logs db
   ```

3. **Permission errors:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

4. **Module import errors:**
   ```bash
   # Rebuild containers
   docker compose build --no-cache
   ```

5. **Data import issues:**
   ```bash
   # Git LFS pointer files (not actual data)
   git lfs pull  # Download actual CSV files
   
   # Verify files are downloaded
   file data/MBList.csv  # Should show "CSV text" not "ASCII text"
   
   # Encoding errors during import
   # The import commands automatically handle multiple encodings
   
   # Memory issues with large datasets
   # Batch processing is built-in, but you can monitor with:
   docker stats
   
   # Import appears stuck
   # Large datasets take time - MycoBank import can take 10-15 minutes
   # Progress is shown every 100 records
   
   # Database space issues
   df -h  # Check available disk space (need ~200MB for full import)
   ```

### Viewing Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs web
docker compose logs db

# Follow logs in real-time
docker compose logs -f web
```

### Entering Containers
```bash
# Shell access to web container
docker compose exec web bash

# Shell access to database
docker compose exec db psql -U foraynl -d foraynl
```

## Production Considerations

This Docker setup is designed for development. For production deployment:

1. Set `DEBUG=False`
2. Use a proper secret key
3. Configure allowed hosts appropriately
4. Set up proper SSL/TLS termination
5. Use a production WSGI server (gunicorn)
6. Implement proper logging and monitoring
7. Set up database backups
8. Use Docker secrets for sensitive data

## Security Notes

- Never commit `.env` files with real credentials
- Change default passwords in production
- Regularly update base Docker images
- Use non-root users in production containers
- Implement proper firewall rules