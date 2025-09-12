"""
Models for Foray ↔ MycoBank matching and the review workflow.

Schema overview
---------------
Source tables (persisted originals):
- ForayFungi2023          : Foray 2023 raw names (org/conf/foray)
- MycoBankList            : MycoBank canonical rows (taxon/current/etc.)

Match artifacts (computed by the pipeline):
- ForayMatch              : 3-column match category per Foray row
- ForayPerfectMatch       : Perfect within-Foray (all three equal)
- ForayMismatchExplanation: Which columns agree / mismatch
- ForayPerfectMycoMatch   : Perfect within-Foray + exact MycoBank hit
- ForayMismatchMycoScores : Similarity scores to MycoBank + chosen candidate

Review workflow:
- ReviewedMatch           : Human review status + validated name
"""

from django.db import models

# ---------------------------------------------------------------------------
# Source tables (originals)
# ---------------------------------------------------------------------------

class ForayFungi2023(models.Model):
    """Original Foray 2023 names (one row per foray_id)."""
    foray_id = models.CharField(max_length=100, primary_key=True)
    genus_and_species_org_entry = models.TextField(null=True, blank=True)
    genus_and_species_conf = models.TextField(null=True, blank=True)
    genus_and_species_foray_name = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["foray_id"]

    def __str__(self) -> str:
        return self.foray_id


class MycoBankList(models.Model):
    """Original MycoBank rows (we prefer current_name over taxon_name)."""
    mycobank_id = models.CharField(max_length=100, primary_key=True)
    taxon_name = models.TextField(null=True, blank=True)
    current_name = models.TextField(null=True, blank=True)
    authors = models.TextField(null=True, blank=True)
    year = models.TextField(null=True, blank=True)
    hyperlink = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["mycobank_id"]

    def __str__(self) -> str:
        return f"{self.mycobank_id} · {self.preferred_name}"

    @property
    def preferred_name(self) -> str:
        """Current name if available; else taxon name."""
        return (self.current_name or self.taxon_name or "").strip()


# ---------------------------------------------------------------------------
# Match artifacts (3-column matching + MycoBank results)
# ---------------------------------------------------------------------------

class ForayMatch(models.Model):
    """
    Result of the 3-column classifier for each Foray row.
    match_category contains codes like:
      - ALL_MATCH, MATCH_ORG_CONF, MATCH_ORG_FORAY, MATCH_CONF_FORAY, ALL_DIFFERENT
    """
    foray_id = models.CharField(max_length=100, db_index=True)
    org_entry = models.CharField(max_length=255)
    conf_name = models.CharField(max_length=255)
    foray_name = models.CharField(max_length=255)  # noqa: F821 (keep name as-is)
    match_category = models.CharField(max_length=50, db_index=True)

    class Meta:
        ordering = ["foray_id"]
        indexes = [
            models.Index(fields=["foray_id"]),
            models.Index(fields=["match_category"]),
        ]

    def __str__(self) -> str:
        return f"{self.foray_id} - {self.match_category}"


class ForayPerfectMatch(models.Model):
    """Perfect within-Foray: org == conf == foray (store the name)."""
    foray_id = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["foray_id"]
        indexes = [models.Index(fields=["foray_id"])]

    def __str__(self) -> str:
        return f"{self.foray_id} · {self.name}"


class ForayMismatchExplanation(models.Model):
    """
    For mismatches: stores the three names and an explanation code:
      ORG_CONF_MATCH, ORG_FORAY_MATCH, CONF_FORAY_MATCH, ALL_DIFFERENT
    """
    foray_id = models.CharField(max_length=100, db_index=True)
    org_entry = models.CharField(max_length=255)
    conf_name = models.CharField(max_length=255)
    foray_name = models.CharField(max_length=255)
    explanation = models.CharField(max_length=100, db_index=True)

    class Meta:
        ordering = ["foray_id"]
        indexes = [
            models.Index(fields=["foray_id"]),
            models.Index(fields=["explanation"]),
        ]

    def __str__(self) -> str:
        return f"{self.foray_id} · {self.explanation}"


class ForayPerfectMycoMatch(models.Model):
    """
    Perfect within-Foray *and* an exact MycoBank hit.
    matched_name is kept for backwards compatibility; mycobank_name is shown in UI.
    """
    foray_id = models.CharField(max_length=100, db_index=True)
    matched_name = models.CharField(max_length=255)
    mycobank_id = models.CharField(max_length=100, db_index=True)
    mycobank_name = models.CharField(max_length=255)

    class Meta:
        ordering = ["foray_id"]
        indexes = [
            models.Index(fields=["foray_id"]),
            models.Index(fields=["mycobank_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.foray_id} → {self.mycobank_id} · {self.mycobank_name}"


class ForayMismatchMycoScores(models.Model):
    """
    For mismatches: similarity scores to MycoBank plus the chosen top candidate.
    mycobank_expl examples: 'ORG → UPDATED', 'CONF → TAXON', 'FORAY → UPDATED'
    """
    foray_id = models.CharField(max_length=100, db_index=True)
    org_score = models.FloatField()
    conf_score = models.FloatField()
    foray_score = models.FloatField()

    # Chosen candidate (filled by the pipeline):
    mycobank_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    mycobank_name = models.CharField(max_length=255, blank=True, null=True)
    mycobank_expl = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        ordering = ["foray_id"]
        indexes = [
            models.Index(fields=["foray_id"]),
            models.Index(fields=["mycobank_id"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.foray_id} → "
            f"org:{self.org_score} conf:{self.conf_score} foray:{self.foray_score}"
        )


# ---------------------------------------------------------------------------
# Review workflow
# ---------------------------------------------------------------------------

class ReviewedMatch(models.Model):
    """
    Reviewer decisions per foray_id.
    - REVIEWED : counted as done, removed from the review queue
    - PENDING  : skipped or reopened; stays in the queue
    - SKIPPED  : optional separate state if you want to distinguish from PENDING
    """
    foray_id = models.CharField(max_length=64, db_index=True, unique=True)
    org_entry = models.CharField(max_length=255, blank=True, null=True)
    conf_name = models.CharField(max_length=255, blank=True, null=True)
    foray_name = models.CharField(max_length=255, blank=True, null=True)

    validated_name = models.CharField(max_length=255, blank=True, null=True)
    reviewer_name = models.CharField(max_length=128, blank=True, null=True)

    STATUS_CHOICES = [
        ("REVIEWED", "Reviewed"),
        ("PENDING",  "Pending"),
        ("SKIPPED",  "Skipped"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="REVIEWED")

    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reviewed_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["reviewed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.foray_id} ({self.status})"
