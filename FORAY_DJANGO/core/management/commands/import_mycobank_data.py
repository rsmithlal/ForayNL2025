"""
Django management command to import MycoBank data from CSV.

Usage:
    python manage.py import_mycobank_data data/MBList.csv
"""

import csv
import os
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import MycoBankList


class Command(BaseCommand):
    help = 'Import MycoBank reference data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing MycoBank data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        clear_existing = options['clear']
        dry_run = options['dry_run']

        # Check if file exists
        if not os.path.exists(csv_file):
            raise CommandError(f'CSV file does not exist: {csv_file}')

        # Check if file is accessible
        try:
            # Try different encodings for the CSV file
            encodings_to_try = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            file_handle = None
            
            for encoding in encodings_to_try:
                try:
                    file_handle = open(csv_file, mode='r', encoding=encoding)
                    # Test if we can read the first line
                    file_handle.readline()
                    file_handle.seek(0)  # Reset to beginning
                    self.stdout.write(f'📄 Successfully opened CSV with {encoding} encoding')
                    break
                except UnicodeDecodeError:
                    if file_handle:
                        file_handle.close()
                    continue
            
            if not file_handle:
                raise CommandError(f"Could not decode CSV file with any of these encodings: {encodings_to_try}")
                
            with file_handle:
                # Check if it's a Git LFS pointer file
                first_line = file_handle.readline().strip()
                if first_line == 'version https://git-lfs.github.com/spec/v1':
                    self.stdout.write(
                        self.style.WARNING(
                            'This appears to be a Git LFS pointer file. '
                            'Please ensure Git LFS is installed and the file is downloaded:\n'
                            '  git lfs pull\n'
                        )
                    )
                    return
        except Exception as e:
            raise CommandError(f'Cannot read CSV file: {e}')

        self.stdout.write(f'🍄 Importing MycoBank data from: {csv_file}')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No data will be imported'))

        try:
            records_processed = self._import_csv_data(csv_file, clear_existing, dry_run)
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Dry run completed. Would import {records_processed} records'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully imported {records_processed} MycoBank records'
                    )
                )

        except Exception as e:
            raise CommandError(f'Import failed: {e}')

    def _import_csv_data(self, csv_file: str, clear_existing: bool, dry_run: bool) -> int:
        """Import CSV data into MycoBankList model."""
        
        # Try different encodings for the CSV file
        encodings_to_try = ['latin-1', 'iso-8859-1', 'cp1252', 'utf-8']  # Start with more permissive encodings
        successful_encoding = None
        
        for encoding in encodings_to_try:
            try:
                # Test full file read capability
                with open(csv_file, mode='r', encoding=encoding) as test_file:
                    # Try to read the entire file to make sure encoding works
                    test_content = test_file.read()
                    successful_encoding = encoding
                    self.stdout.write(f'📄 Using {encoding} encoding for CSV processing')
                    break
            except UnicodeDecodeError:
                continue
        
        if not successful_encoding:
            raise Exception(f"Could not decode CSV file with any encoding: {encodings_to_try}")
            
        with open(csv_file, mode='r', encoding=successful_encoding) as file_handle:
            # Auto-detect dialect using a small sample
            sample = file_handle.read(1024)
            file_handle.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            file_handle.seek(0)
            
            reader = csv.DictReader(file_handle, dialect=dialect)
            
            # Map CSV columns to model fields (case insensitive)
            header_map = {}
            for col in reader.fieldnames or []:
                col_lower = col.lower().strip()
                # MycoBank # column maps to mycobank_id
                if 'mycobank' in col_lower and '#' in col_lower:
                    header_map['mycobank_id'] = col
                elif col_lower == 'id':  # Could also be a simple ID column
                    header_map['mycobank_id'] = col
                elif 'taxon name' in col_lower or col_lower == 'taxon name':
                    header_map['taxon_name'] = col
                elif 'current name' in col_lower and 'taxon name' in col_lower:
                    header_map['current_name'] = col
                elif col_lower == 'authors':
                    header_map['authors'] = col
                elif 'year' in col_lower and 'publication' in col_lower:
                    header_map['year'] = col
                elif col_lower == 'hyperlink':
                    header_map['hyperlink'] = col

            fieldnames = reader.fieldnames or []
            self.stdout.write(f'📋 CSV columns found: {list(fieldnames)}')
            self.stdout.write(f'🗂️  Column mapping: {header_map}')

            if not header_map.get('mycobank_id'):
                raise CommandError('Cannot find mycobank_id column in CSV')

            if clear_existing and not dry_run:
                self.stdout.write('🗑️  Clearing existing MycoBankList data...')
                MycoBankList.objects.all().delete()

            records_to_create = []
            processed_count = 0
            errors = []
            batch_size = 1000  # Process in batches to manage memory
            total_created = 0

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Extract data using column mapping
                    mycobank_id = row.get(header_map.get('mycobank_id', ''), '').strip()
                    
                    if not mycobank_id:
                        errors.append(f'Row {row_num}: Missing mycobank_id')
                        continue

                    record_data = {
                        'mycobank_id': mycobank_id,
                        'taxon_name': row.get(
                            header_map.get('taxon_name', ''), ''
                        ).strip() or None,
                        'current_name': row.get(
                            header_map.get('current_name', ''), ''
                        ).strip() or None,
                        'authors': row.get(
                            header_map.get('authors', ''), ''
                        ).strip() or None,
                        'year': row.get(
                            header_map.get('year', ''), ''
                        ).strip() or None,
                        'hyperlink': row.get(
                            header_map.get('hyperlink', ''), ''
                        ).strip() or None,
                    }

                    if dry_run:
                        processed_count += 1
                        if processed_count <= 5:  # Show first 5 records in dry run
                            self.stdout.write(f'  🍄 Would create: {record_data}')
                    else:
                        records_to_create.append(MycoBankList(**record_data))

                    processed_count += 1

                    # Batch insert when we reach batch_size records
                    if not dry_run and len(records_to_create) >= batch_size:
                        with transaction.atomic():
                            created_objects = MycoBankList.objects.bulk_create(
                                records_to_create,
                                batch_size=500,
                                ignore_conflicts=True  # Skip duplicates
                            )
                            total_created += len(created_objects)
                        records_to_create = []  # Clear the batch

                    # Progress indicator
                    if processed_count % 100 == 0:
                        self.stdout.write(f'  📈 Processed {processed_count} records...')

                except Exception as e:
                    errors.append(f'Row {row_num}: {e}')

            # Insert any remaining records
            if not dry_run and records_to_create:
                with transaction.atomic():
                    created_objects = MycoBankList.objects.bulk_create(
                        records_to_create,
                        batch_size=500,
                        ignore_conflicts=True  # Skip duplicates
                    )
                    total_created += len(created_objects)

            # Show errors if any
            if errors:
                self.stdout.write(self.style.WARNING(f'⚠️  {len(errors)} errors encountered:'))
                for error in errors[:10]:  # Show first 10 errors
                    self.stdout.write(f'    {error}')
                if len(errors) > 10:
                    self.stdout.write(f'    ... and {len(errors) - 10} more errors')
                    
            # Show final creation count
            if not dry_run:
                self.stdout.write(f'💾 Total records created: {total_created}')

            return processed_count