"""
Django management command to import Foray 2023 fungi data from CSV.

Usage:
    python manage.py import_foray_data data/2023ForayNL_Fungi.csv
"""

import csv
import os
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import ForayFungi2023


class Command(BaseCommand):
    help = 'Import Foray 2023 fungi data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing Foray fungi data'
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
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Check if it's a Git LFS pointer file
                first_line = f.readline().strip()
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

        self.stdout.write(f'📊 Importing Foray fungi data from: {csv_file}')

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
                        f'✅ Successfully imported {records_processed} Foray fungi records'
                    )
                )

        except Exception as e:
            raise CommandError(f'Import failed: {e}')

    def _import_csv_data(self, csv_file: str, clear_existing: bool, dry_run: bool) -> int:
        """Import CSV data into ForayFungi2023 model."""
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            # Auto-detect dialect
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            
            reader = csv.DictReader(f, dialect=dialect)
            
            # Validate expected columns
            expected_columns = {
                'foray_id', 
                'genus_and_species_org_entry',
                'genus_and_species_conf', 
                'genus_and_species_foray_name'
            }
            
            # Check for column variations (case insensitive)
            header_map = {}
            for col in reader.fieldnames or []:
                col_lower = col.lower().strip()
                # Look for ID column (could be 'id', 'foray_id', etc.)
                if col_lower == 'id' or ('foray' in col_lower and 'id' in col_lower):
                    header_map['foray_id'] = col
                elif 'genus_and_species_org_entry' in col_lower:
                    header_map['genus_and_species_org_entry'] = col
                elif 'genus_and_species_conf' in col_lower:
                    header_map['genus_and_species_conf'] = col
                elif 'genus_and_species_foray_name' in col_lower:
                    header_map['genus_and_species_foray_name'] = col

            self.stdout.write(f'📋 CSV columns found: {list(reader.fieldnames)}')
            self.stdout.write(f'🗂️  Column mapping: {header_map}')

            if not header_map.get('foray_id'):
                raise CommandError('Cannot find foray_id column in CSV')

            if clear_existing and not dry_run:
                self.stdout.write('🗑️  Clearing existing ForayFungi2023 data...')
                ForayFungi2023.objects.all().delete()

            records_to_create = []
            processed_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Extract data using column mapping
                    foray_id = row.get(header_map.get('foray_id', ''), '').strip()
                    
                    if not foray_id:
                        errors.append(f'Row {row_num}: Missing foray_id')
                        continue

                    record_data = {
                        'foray_id': foray_id,
                        'genus_and_species_org_entry': row.get(
                            header_map.get('genus_and_species_org_entry', ''), ''
                        ).strip() or None,
                        'genus_and_species_conf': row.get(
                            header_map.get('genus_and_species_conf', ''), ''
                        ).strip() or None,
                        'genus_and_species_foray_name': row.get(
                            header_map.get('genus_and_species_foray_name', ''), ''
                        ).strip() or None,
                    }

                    if dry_run:
                        processed_count += 1
                        if processed_count <= 5:  # Show first 5 records in dry run
                            self.stdout.write(f'  📝 Would create: {record_data}')
                    else:
                        records_to_create.append(ForayFungi2023(**record_data))

                    processed_count += 1

                    # Progress indicator
                    if processed_count % 100 == 0:
                        self.stdout.write(f'  📈 Processed {processed_count} records...')

                except Exception as e:
                    errors.append(f'Row {row_num}: {e}')

            # Show errors if any
            if errors:
                self.stdout.write(self.style.WARNING(f'⚠️  {len(errors)} errors encountered:'))
                for error in errors[:10]:  # Show first 10 errors
                    self.stdout.write(f'    {error}')
                if len(errors) > 10:
                    self.stdout.write(f'    ... and {len(errors) - 10} more errors')

            # Bulk create records if not dry run
            if not dry_run and records_to_create:
                with transaction.atomic():
                    ForayFungi2023.objects.bulk_create(
                        records_to_create,
                        batch_size=500,
                        ignore_conflicts=True  # Skip duplicates
                    )

            return processed_count