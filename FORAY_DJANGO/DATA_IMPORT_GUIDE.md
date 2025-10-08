# Data Import Guide

This guide covers importing taxonomic fungi data into the ForayNL Django application.

## Overview

The ForayNL application supports importing large taxonomic datasets for fungi identification and matching. The system handles two primary data sources:

1. **Foray Fungi Data**: Local observations from ForayNL 2023 (~983 records)
2. **MycoBank Database**: Comprehensive taxonomic reference (~537,509 records)

## Prerequisites

### Git LFS Setup
Large CSV files are managed using Git LFS. Ensure you have the actual data files:

```bash
# Check if Git LFS is installed
git lfs version

# Download large files from LFS
git lfs pull

# Verify files are downloaded (not pointer files)
ls -la data/
# Should show actual file sizes, not ~130 bytes
```

### Docker Environment
All import commands run within the containerized Django environment:

```bash
# Ensure containers are built and running
docker compose up -d db redis

# Test database connectivity
docker compose run --rm test python manage.py check --database default
```

## Data Sources

### ForayNL 2023 Dataset
- **File**: `data/2023ForayNL_Fungi.csv`  
- **Size**: ~375KB
- **Records**: 983 fungi observations
- **Fields**: ID, species names, habitat, substrate, tree species, photos
- **Purpose**: Local observation data for matching against taxonomic references

### MycoBank Dataset  
- **File**: `data/MBList.csv`
- **Size**: ~390MB
- **Records**: 537,509 taxonomic entries
- **Fields**: MycoBank ID, taxon names, authors, publication years, hyperlinks
- **Purpose**: Comprehensive taxonomic reference database

## Import Commands

### Django Management Commands

The application provides three custom management commands:

#### 1. import_foray_data
```bash
# Basic import
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv

# Preview without importing (dry run)
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv --dry-run

# Clear existing data before import
docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv --clear
```

#### 2. import_mycobank_data
```bash
# Basic import (takes 10-15 minutes)
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv

# Clear existing data before import
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv --clear

# Preview import (shows first 5 records)
docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv --dry-run
```

#### 3. data_stats
```bash
# View comprehensive database statistics
docker compose run --rm web python manage.py data_stats
```

## Import Process

### Step-by-Step Workflow

1. **Prepare Environment**
   ```bash
   # Start database services
   docker compose up -d db redis
   
   # Verify Git LFS files are downloaded
   git lfs pull
   ls -la data/
   ```

2. **Import Foray Data** (Small dataset first)
   ```bash
   docker compose run --rm web python manage.py import_foray_data data/2023ForayNL_Fungi.csv
   ```
   
   Expected output:
   ```
   📊 Importing Foray fungi data from: data/2023ForayNL_Fungi.csv
   📋 CSV columns found: ['id', 'genus_and_species_org_entry', ...]
   🗂️  Column mapping: {'foray_id': 'id', ...}
   📈 Processed 100 records...
   📈 Processed 900 records...
   ✅ Successfully imported 983 Foray fungi records
   ```

3. **Import MycoBank Data** (Large dataset)
   ```bash
   docker compose run --rm web python manage.py import_mycobank_data data/MBList.csv
   ```
   
   Expected output (takes 10-15 minutes):
   ```
   📄 Using latin-1 encoding for CSV processing
   🍄 Importing MycoBank data from: data/MBList.csv
   📋 CSV columns found: ['ID', 'Taxon name', 'Authors', ...]
   🗂️  Column mapping: {'mycobank_id': 'MycoBank #', ...}
   📈 Processed 100 records...
   📈 Processed 100000 records...
   📈 Processed 500000 records...
   💾 Total records created: 537483
   ✅ Successfully imported 537483 MycoBank records
   ```

4. **Verify Import Success**
   ```bash
   docker compose run --rm web python manage.py data_stats
   ```
   
   Expected results:
   ```
   📊 ForayNL Data Statistics
   ==================================================
   🗂️  Source Data:
     📋 Foray Fungi 2023: 983 records
     🍄 MycoBank List: 537,483 records
   🏥 Database Health:
     💾 Database Size: 183 MB
   ✅ Data statistics complete!
   ```

## Technical Features

### Performance Optimizations

- **Batch Processing**: Records processed in 1,000-record batches to manage memory
- **Transaction Safety**: Atomic database operations prevent partial imports
- **Progress Tracking**: Real-time indicators every 100 records
- **Memory Management**: Automatic cleanup of processed batches

### Error Handling

- **Encoding Detection**: Automatic handling of UTF-8, Latin-1, ISO-8859-1, CP1252
- **Malformed Records**: Graceful handling with detailed error reporting
- **Duplicate Prevention**: `ignore_conflicts=True` allows safe re-running
- **Validation**: Required field checking and data type validation

### Data Quality

- **Column Mapping**: Flexible mapping handles CSV structure variations
- **Field Validation**: Ensures data integrity during import
- **Statistics Tracking**: Comprehensive metrics on success rates
- **Coverage Analysis**: Percentage coverage reports for key fields

## Troubleshooting

### Git LFS Issues
```bash
# Problem: CSV files are small (~130 bytes) - these are pointer files
# Solution: Download actual files
git lfs pull

# Verify download
file data/MBList.csv  # Should show "CSV text" not "ASCII text"
```

### Encoding Errors
```bash
# Problem: UnicodeDecodeError during import
# Solution: Import commands automatically try multiple encodings
# If persistent, check file integrity:
head -10 data/MBList.csv
```

### Memory Issues
```bash
# Problem: Import process killed or hangs
# Solution: Monitor Docker container resources
docker stats

# Ensure sufficient disk space
df -h  # Need ~200MB available
```

### Import Appears Stuck
```bash
# MycoBank import takes 10-15 minutes for 537K records
# Progress shown every 100 records
# Monitor Docker logs for progress:
docker compose logs -f web
```

### Database Connection Issues
```bash
# Restart database service
docker compose restart db

# Check database status
docker compose run --rm web python manage.py check --database default

# View database logs
docker compose logs db
```

## Data Usage

After successful import, the application provides:

- **Taxonomic Matching**: Match Foray observations against MycoBank reference data
- **Search Functionality**: Query by species names, authors, or MycoBank IDs
- **Data Validation**: Cross-reference local observations with authoritative taxonomy
- **Statistical Analysis**: Data quality and coverage metrics

## Performance Metrics

### Expected Import Times
- **Foray Data**: ~10-30 seconds (983 records)
- **MycoBank Data**: ~10-15 minutes (537,509 records)

### Database Growth
- **Initial**: ~8MB (empty schema)
- **After Foray Import**: ~8.2MB (+248KB)
- **After MycoBank Import**: ~183MB (+174MB)

### Success Rates
- **Foray Import**: 100% success rate (983/983 records)
- **MycoBank Import**: 99.995% success rate (537,483/537,509 records)

## Next Steps

After successful data import:

1. **Explore the Web Interface**: Visit http://localhost:8000
2. **Test Matching Functionality**: Use the taxonomic matching features
3. **Review Data Quality**: Use the admin interface to browse imported data
4. **Run Application Tests**: Verify functionality with `docker compose run --rm test pytest`