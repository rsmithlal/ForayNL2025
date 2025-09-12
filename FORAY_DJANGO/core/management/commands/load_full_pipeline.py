# core/management/commands/load_full_pipeline.py
from django.core.management.base import BaseCommand
from core.logic.full_match_pipeline import run_pipeline
from core.models import (ForayPerfectMatch, ForayMismatchExplanation,
                         ForayPerfectMycoMatch, ForayMismatchMycoScores)

class Command(BaseCommand):
    help = "Run the full matching pipeline and populate all result tables"

    def handle(self, *args, **kwargs):
        ForayPerfectMatch.objects.all().delete()
        ForayMismatchExplanation.objects.all().delete()
        ForayPerfectMycoMatch.objects.all().delete()
        ForayMismatchMycoScores.objects.all().delete()

        perfect, mismatch, perfect_myco, scores = run_pipeline()

        ForayPerfectMatch.objects.bulk_create(
            [ForayPerfectMatch(foray_id=r["foray_id"], name=r["name"]) for r in perfect]
        )
        ForayMismatchExplanation.objects.bulk_create([ForayMismatchExplanation(**r) for r in mismatch])
        ForayPerfectMycoMatch.objects.bulk_create([ForayPerfectMycoMatch(**r) for r in perfect_myco])
        ForayMismatchMycoScores.objects.bulk_create([ForayMismatchMycoScores(**r) for r in scores])

        self.stdout.write(self.style.SUCCESS("✅ All tables populated."))
