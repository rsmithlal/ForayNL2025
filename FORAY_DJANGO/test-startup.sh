#!/bin/bash
# test-startup.sh - Test environment startup script

set -e  # Exit on any error

echo "🧪 Starting ForayNL Test Environment"
echo "===================================="

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
until python manage.py check --database default > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 2
done
echo "✅ Database connection established"

# Run database migrations for test environment
echo "🗄️  Setting up test database..."
python manage.py migrate --noinput

# Run Django system checks
echo "🔍 Running Django system checks..."
python manage.py check

echo "🧪 Running test suite with coverage..."
echo ""

# Run the test suite with coverage reporting
exec pytest --cov=core --cov-report=html --cov-report=term-missing -v