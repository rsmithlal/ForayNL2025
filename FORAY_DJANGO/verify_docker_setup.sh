#!/bin/bash
# verify_docker_setup.sh - Test Docker containerization setup

echo "🐳 ForayNL Django Docker Setup Verification"
echo "==========================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Navigate to the Django project directory
cd "$(dirname "$0")" || exit 1

echo "📂 Current directory: $(pwd)"

# Check required files exist
required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "requirements-dev.txt"
    "manage.py"
    "pytest.ini"
)

echo "📋 Checking required files..."
for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

echo ""
echo "🔧 Building Docker containers..."
docker compose build

if [[ $? -ne 0 ]]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker build completed successfully"

echo ""
echo "🚀 Starting services..."
docker compose up -d db redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Check if database is responding
echo "🔍 Testing database connection..."
docker compose run --rm test python -c "
import os
import django
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

if [[ $? -ne 0 ]]; then
    echo "❌ Database connection test failed"
    docker compose down
    exit 1
fi

echo ""
echo "🧪 Running Django checks..."
docker compose run --rm test python manage.py check

if [[ $? -ne 0 ]]; then
    echo "❌ Django check failed"
    docker compose down
    exit 1
fi

echo "✅ Django check passed"

echo ""
echo "🗄️  Running migrations..."
docker compose run --rm test python manage.py migrate

if [[ $? -ne 0 ]]; then
    echo "❌ Migrations failed"
    docker compose down
    exit 1
fi

echo "✅ Migrations completed successfully"

echo ""
echo "🧪 Running pytest test suite..."
docker compose run --rm test pytest -v

test_result=$?

echo ""
echo "🧹 Cleaning up..."
docker compose down

if [[ $test_result -eq 0 ]]; then
    echo ""
    echo "🎉 SUCCESS! Docker setup verification completed successfully"
    echo "   - Docker containers build correctly"
    echo "   - Database connection works"
    echo "   - Django configuration is valid"
    echo "   - Migrations run successfully"
    echo "   - Test suite executes without errors"
    echo ""
    echo "💡 To start development:"
    echo "   docker compose up"
    echo ""
    echo "💡 To run tests:"
    echo "   docker compose run --rm test pytest"
    exit 0
else
    echo ""
    echo "❌ FAILURE! Test suite failed"
    echo "   Please review the test output above for details"
    exit 1
fi