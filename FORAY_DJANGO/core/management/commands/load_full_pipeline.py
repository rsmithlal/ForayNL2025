from django.core.management.base import BaseCommand
from core.logic.full_match_pipeline import run_pipeline
from core.models import (
    ForayPerfectMatch,
    ForayMismatchExplanation,
    ForayPerfectMycoMatch,
    ForayMismatchMycoScores,
    ForayMatch,                # <-- add
    ForayFungi2023,           # <-- add
)

class Command(BaseCommand):
    help = 'Run the matching pipeline and populate all result tables'

    def handle(self, *args, **kwargs):
        import time
        start_time = time.time()
        
        self.stdout.write("🗑️  Clearing existing match tables...")
        
        # Clear old records with progress
        tables = [
            ("ForayPerfectMatch", ForayPerfectMatch),
            ("ForayMismatchExplanation", ForayMismatchExplanation), 
            ("ForayPerfectMycoMatch", ForayPerfectMycoMatch),
            ("ForayMismatchMycoScores", ForayMismatchMycoScores),
            ("ForayMatch", ForayMatch)
        ]
        
        for table_name, model in tables:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"   ✓ {table_name}: {count:,} records cleared")
        
        self.stdout.write("\n🚀 Starting matching pipeline...")
        
        # run pipeline
        perfect_list, mismatch_list, perfect_myco, mismatch_scores = run_pipeline()

        self.stdout.write("\n💾 Populating database tables...")
        
        # write main tables with progress
        operations = [
            ("ForayPerfectMatch", ForayPerfectMatch, [
                ForayPerfectMatch(foray_id=row['foray_id'], name=row['name'])
                for row in perfect_list
            ]),
            ("ForayMismatchExplanation", ForayMismatchExplanation, [
                ForayMismatchExplanation(**row) for row in mismatch_list
            ]),
            ("ForayPerfectMycoMatch", ForayPerfectMycoMatch, [
                ForayPerfectMycoMatch(**row) for row in perfect_myco
            ]),
            ("ForayMismatchMycoScores", ForayMismatchMycoScores, [
                ForayMismatchMycoScores(**row) for row in mismatch_scores
            ])
        ]
        
        for table_name, model, objects in operations:
            if objects:
                model.objects.bulk_create(objects, batch_size=1000)
                self.stdout.write(f"   ✓ {table_name}: {len(objects):,} records inserted")
            else:
                self.stdout.write(f"   - {table_name}: No records to insert")

        # --- NEW: also build ForayMatch so the browser has data ---
        # perfect rows need the three Foray columns; fetch from ForayFungi2023
        fids_perfect = [p['foray_id'] for p in perfect_list]
        f_map = {
            f.foray_id: f for f in ForayFungi2023.objects.filter(foray_id__in=fids_perfect)
        }

        match_rows = []
        for p in perfect_list:
            f = f_map.get(p['foray_id'])
            if not f:
                continue
            match_rows.append(ForayMatch(
                foray_id=p['foray_id'],
                org_entry=f.genus_and_species_org_entry or '',
                conf_name=f.genus_and_species_conf or '',
                foray_name=f.genus_and_species_foray_name or '',
                match_category='ALL_MATCH',
            ))

        # mismatch rows can map explanation directly to category
        valid = {'ORG_CONF_MATCH','ORG_FORAY_MATCH','CONF_FORAY_MATCH','ALL_DIFFERENT'}
        for m in mismatch_list:
            cat = m.get('explanation') if m.get('explanation') in valid else 'ALL_DIFFERENT'
            match_rows.append(ForayMatch(
                foray_id=m['foray_id'],
                org_entry=m['org_entry'],
                conf_name=m['conf_name'],
                foray_name=m['foray_name'],
                match_category=cat,
            ))

        # Create unified ForayMatch table
        if match_rows:
            ForayMatch.objects.bulk_create(match_rows, batch_size=1000)
            self.stdout.write(f"   ✓ ForayMatch (unified): {len(match_rows):,} records inserted")
        else:
            self.stdout.write(f"   - ForayMatch (unified): No records to insert")
        
        # Final summary
        elapsed = time.time() - start_time
        self.stdout.write(f"\n🎉 Pipeline completed successfully in {elapsed:.1f} seconds!")
        self.stdout.write(self.style.SUCCESS(f"📊 Summary: {len(perfect_list)} perfect matches, {len(mismatch_list)} mismatches processed"))
