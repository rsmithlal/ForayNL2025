"""
Django management command to show data statistics and health checks.

Usage:
    python manage.py data_stats
"""

from django.core.management.base import BaseCommand
from django.db import connection

from core.models import (
    ForayFungi2023, 
    MycoBankList, 
    ForayMatch,
    ForayPerfectMatch,
    ReviewedMatch
)


class Command(BaseCommand):
    help = 'Show data statistics and health information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics'
        )

    def handle(self, *args, **options):
        detailed = options['detailed']

        self.stdout.write('📊 ForayNL Data Statistics')
        self.stdout.write('=' * 50)

        # Source data statistics
        self._show_source_stats()
        
        # Match artifacts statistics
        self._show_match_stats()
        
        # Review workflow statistics
        self._show_review_stats()

        if detailed:
            self._show_detailed_stats()

        # Database health
        self._show_database_health()

    def _show_source_stats(self):
        """Show statistics for source data tables."""
        self.stdout.write('\n🗂️  Source Data:')
        
        # ForayFungi2023 stats
        foray_count = ForayFungi2023.objects.count()
        self.stdout.write(f'  📋 Foray Fungi 2023: {foray_count:,} records')
        
        if foray_count > 0:
            # Sample statistics
            with_org = ForayFungi2023.objects.exclude(genus_and_species_org_entry__isnull=True).count()
            with_conf = ForayFungi2023.objects.exclude(genus_and_species_conf__isnull=True).count()
            with_foray = ForayFungi2023.objects.exclude(genus_and_species_foray_name__isnull=True).count()
            
            self.stdout.write(f'    • With org entry: {with_org:,} ({with_org/foray_count*100:.1f}%)')
            self.stdout.write(f'    • With conf name: {with_conf:,} ({with_conf/foray_count*100:.1f}%)')
            self.stdout.write(f'    • With foray name: {with_foray:,} ({with_foray/foray_count*100:.1f}%)')

        # MycoBankList stats
        mycobank_count = MycoBankList.objects.count()
        self.stdout.write(f'  🍄 MycoBank List: {mycobank_count:,} records')
        
        if mycobank_count > 0:
            with_current = MycoBankList.objects.exclude(current_name__isnull=True).count()
            with_taxon = MycoBankList.objects.exclude(taxon_name__isnull=True).count()
            with_authors = MycoBankList.objects.exclude(authors__isnull=True).count()
            
            self.stdout.write(f'    • With current name: {with_current:,} ({with_current/mycobank_count*100:.1f}%)')
            self.stdout.write(f'    • With taxon name: {with_taxon:,} ({with_taxon/mycobank_count*100:.1f}%)')
            self.stdout.write(f'    • With authors: {with_authors:,} ({with_authors/mycobank_count*100:.1f}%)')

    def _show_match_stats(self):
        """Show statistics for match artifacts."""
        self.stdout.write('\n🔍 Match Artifacts:')
        
        # ForayMatch stats
        match_count = ForayMatch.objects.count()
        self.stdout.write(f'  📊 Foray Matches: {match_count:,} records')
        
        if match_count > 0:
            # Match category breakdown
            from django.db.models import Count
            categories = ForayMatch.objects.values('match_category').annotate(count=Count('id')).order_by('-count')
            for cat in categories[:5]:  # Top 5 categories
                self.stdout.write(f'    • {cat["match_category"]}: {cat["count"]:,}')

        # Perfect matches
        perfect_count = ForayPerfectMatch.objects.count()
        self.stdout.write(f'  ✅ Perfect Matches: {perfect_count:,} records')

    def _show_review_stats(self):
        """Show statistics for review workflow."""
        self.stdout.write('\n👥 Review Workflow:')
        
        reviewed_count = ReviewedMatch.objects.count()
        self.stdout.write(f'  📝 Reviewed Matches: {reviewed_count:,} records')
        
        if reviewed_count > 0:
            # Status breakdown
            from django.db.models import Count
            statuses = ReviewedMatch.objects.values('status').annotate(count=Count('id')).order_by('-count')
            for status in statuses:
                self.stdout.write(f'    • {status["status"]}: {status["count"]:,}')

    def _show_detailed_stats(self):
        """Show detailed statistics and sample data."""
        self.stdout.write('\n🔬 Detailed Statistics:')
        
        # Sample Foray records
        if ForayFungi2023.objects.exists():
            self.stdout.write('\n  📋 Sample Foray Records:')
            for record in ForayFungi2023.objects.all()[:3]:
                self.stdout.write(f'    {record.foray_id}: {record.genus_and_species_org_entry}')

        # Sample MycoBank records
        if MycoBankList.objects.exists():
            self.stdout.write('\n  🍄 Sample MycoBank Records:')
            for record in MycoBankList.objects.all()[:3]:
                self.stdout.write(f'    {record.mycobank_id}: {record.preferred_name}')

    def _show_database_health(self):
        """Show database health information."""
        self.stdout.write('\n🏥 Database Health:')
        
        try:
            with connection.cursor() as cursor:
                # Database size (PostgreSQL specific)
                cursor.execute("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size
                """)
                db_size = cursor.fetchone()[0]
                self.stdout.write(f'  💾 Database Size: {db_size}')
                
                # Table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 5
                """)
                
                self.stdout.write('  📊 Largest Tables:')
                for schema, table, size in cursor.fetchall():
                    self.stdout.write(f'    • {table}: {size}')
                    
        except Exception as e:
            self.stdout.write(f'  ⚠️  Could not retrieve database health: {e}')

        self.stdout.write(f'\n✅ Data statistics complete!')