#!/bin/bash
# startup.sh - Django web application startup script

set -e  # Exit on any error

echo "🚀 Starting ForayNL Django Application"
echo "======================================"

# Wait for database to be ready
echo "⏳ Waiting for database connection..."
until python manage.py check --database default > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 2
done
echo "✅ Database connection established"

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Check if we have data to import (optional)
if [ -f "data/2023ForayNL_Fungi.csv" ] && [ -f "data/MBList.csv" ]; then
    echo "📊 Checking for data import..."
    
    # Check if data is already imported
    foray_count=$(python manage.py shell -c "from core.models import ForayFungi2023; print(ForayFungi2023.objects.count())" 2>/dev/null || echo "0")
    mycobank_count=$(python manage.py shell -c "from core.models import MycoBankList; print(MycoBankList.objects.count())" 2>/dev/null || echo "0")
    
    if [ "$foray_count" -eq "0" ]; then
        echo "🔄 Importing Foray fungi data..."
        python manage.py import_foray_data data/2023ForayNL_Fungi.csv
    else
        echo "✅ Foray data already imported ($foray_count records)"
    fi
    
    if [ "$mycobank_count" -eq "0" ]; then
        echo "🔄 Importing MycoBank data..."
        python manage.py import_mycobank_data data/MBList.csv
    else
        echo "✅ MycoBank data already imported ($mycobank_count records)"
    fi
else
    echo "⚠️  Data files not found - skipping import"
fi

# Run Django system checks
echo "🔍 Running Django system checks..."
python manage.py check

echo "🎉 Startup complete! Starting Django development server..."
echo "🌐 Application will be available at http://localhost:8000"
echo ""

# Start the Django development server
exec python manage.py runserver 0.0.0.0:8000