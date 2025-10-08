from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Q, Count, Avg, Max, Min, F
from .models import (
    ForayFungi2023, MycoBankList,
    ForayMatch, ForayPerfectMatch, ForayMismatchExplanation,
    ForayPerfectMycoMatch, ForayMismatchMycoScores, ReviewedMatch
)

# Customize admin site headers
admin.site.site_header = "🍄 ForayNL Fungi Matching System"
admin.site.site_title = "ForayNL Admin"
admin.site.index_title = "Welcome to ForayNL Administration"


# ---------------------------------------------------------------------------
# Custom Filter Classes
# ---------------------------------------------------------------------------

class NameConsistencyFilter(admin.SimpleListFilter):
    """Filter Foray records by name consistency across the three variants."""
    title = '🎯 Name Consistency'
    parameter_name = 'name_consistency'

    def lookups(self, request, model_admin):
        return [
            ('all_match', '✅ All Names Match'),
            ('partial_match', '⚠️ Partial Match (2 of 3)'),
            ('all_different', '❌ All Different'),
            ('has_empty', '⭕ Has Empty Names'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'all_match':
            return queryset.filter(
                genus_and_species_org_entry=F('genus_and_species_conf'),
                genus_and_species_conf=F('genus_and_species_foray_name')
            )
        elif self.value() == 'partial_match':
            # Two names match but not all three
            return queryset.filter(
                Q(genus_and_species_org_entry=F('genus_and_species_conf')) |
                Q(genus_and_species_org_entry=F('genus_and_species_foray_name')) |
                Q(genus_and_species_conf=F('genus_and_species_foray_name'))
            ).exclude(
                genus_and_species_org_entry=F('genus_and_species_conf'),
                genus_and_species_conf=F('genus_and_species_foray_name')
            )
        elif self.value() == 'all_different':
            return queryset.exclude(
                Q(genus_and_species_org_entry=F('genus_and_species_conf')) |
                Q(genus_and_species_org_entry=F('genus_and_species_foray_name')) |
                Q(genus_and_species_conf=F('genus_and_species_foray_name'))
            )
        elif self.value() == 'has_empty':
            return queryset.filter(
                Q(genus_and_species_org_entry__isnull=True) |
                Q(genus_and_species_org_entry__exact='') |
                Q(genus_and_species_conf__isnull=True) |
                Q(genus_and_species_conf__exact='') |
                Q(genus_and_species_foray_name__isnull=True) |
                Q(genus_and_species_foray_name__exact='')
            )
        return queryset


class MatchingStatusFilter(admin.SimpleListFilter):
    """Filter records by their matching status and results."""
    title = '🔍 Matching Status'
    parameter_name = 'matching_status'

    def lookups(self, request, model_admin):
        return [
            ('has_perfect_match', '🎯 Has Perfect MycoBank Match'),
            ('has_candidate_match', '📊 Has Candidate Matches'),
            ('no_matches', '❌ No Matches Found'),
            ('reviewed', '👤 Human Reviewed'),
            ('pending_review', '⏳ Pending Review'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'has_perfect_match':
            return queryset.filter(
                foray_id__in=ForayPerfectMycoMatch.objects.values_list('foray_id', flat=True)
            )
        elif self.value() == 'has_candidate_match':
            return queryset.filter(
                foray_id__in=ForayMismatchMycoScores.objects.exclude(
                    mycobank_id__isnull=True
                ).values_list('foray_id', flat=True)
            )
        elif self.value() == 'no_matches':
            perfect_ids = ForayPerfectMycoMatch.objects.values_list('foray_id', flat=True)
            candidate_ids = ForayMismatchMycoScores.objects.exclude(
                mycobank_id__isnull=True
            ).values_list('foray_id', flat=True)
            return queryset.exclude(foray_id__in=perfect_ids).exclude(foray_id__in=candidate_ids)
        elif self.value() == 'reviewed':
            return queryset.filter(
                foray_id__in=ReviewedMatch.objects.filter(
                    status='REVIEWED'
                ).values_list('foray_id', flat=True)
            )
        elif self.value() == 'pending_review':
            return queryset.filter(
                foray_id__in=ReviewedMatch.objects.filter(
                    status__in=['PENDING', 'SKIPPED']
                ).values_list('foray_id', flat=True)
            )
        return queryset


class ScoreRangeFilter(admin.SimpleListFilter):
    """Filter by similarity score ranges."""
    title = '📊 Score Range'
    parameter_name = 'score_range'

    def lookups(self, request, model_admin):
        return [
            ('excellent', '🟢 Excellent (90-100%)'),
            ('good', '🟡 Good (70-89%)'),
            ('poor', '🔴 Poor (0-69%)'),
            ('no_scores', '➖ No Scores Available'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'excellent':
            return queryset.filter(
                Q(org_score__gte=90) | Q(conf_score__gte=90) | Q(foray_score__gte=90)
            )
        elif self.value() == 'good':
            return queryset.filter(
                (Q(org_score__gte=70) & Q(org_score__lt=90)) |
                (Q(conf_score__gte=70) & Q(conf_score__lt=90)) |
                (Q(foray_score__gte=70) & Q(foray_score__lt=90))
            ).exclude(
                Q(org_score__gte=90) | Q(conf_score__gte=90) | Q(foray_score__gte=90)
            )
        elif self.value() == 'poor':
            return queryset.filter(
                org_score__lt=70,
                conf_score__lt=70,
                foray_score__lt=70
            )
        return queryset


class MycoBankCompleteness(admin.SimpleListFilter):
    """Filter MycoBank records by data completeness."""
    title = '📋 Data Completeness'
    parameter_name = 'completeness'

    def lookups(self, request, model_admin):
        return [
            ('complete', '✅ Complete (all fields)'),
            ('missing_current', '🔄 Missing Current Name'),
            ('missing_authors', '👤 Missing Authors'),
            ('missing_year', '📅 Missing Year'), 
            ('missing_link', '🔗 Missing Hyperlink'),
            ('minimal', '⚠️ Minimal Data Only'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'complete':
            return queryset.exclude(
                Q(current_name__isnull=True) | Q(current_name__exact='') |
                Q(authors__isnull=True) | Q(authors__exact='') |
                Q(year__isnull=True) | Q(year__exact='') |
                Q(hyperlink__isnull=True) | Q(hyperlink__exact='')
            )
        elif self.value() == 'missing_current':
            return queryset.filter(
                Q(current_name__isnull=True) | Q(current_name__exact='')
            )
        elif self.value() == 'missing_authors':
            return queryset.filter(
                Q(authors__isnull=True) | Q(authors__exact='')
            )
        elif self.value() == 'missing_year':
            return queryset.filter(
                Q(year__isnull=True) | Q(year__exact='')
            )
        elif self.value() == 'missing_link':
            return queryset.filter(
                Q(hyperlink__isnull=True) | Q(hyperlink__exact='')
            )
        elif self.value() == 'minimal':
            return queryset.filter(
                Q(current_name__isnull=True) | Q(current_name__exact=''),
                Q(authors__isnull=True) | Q(authors__exact=''),
                Q(year__isnull=True) | Q(year__exact='')
            )
        return queryset


class PublicationDecadeFilter(admin.SimpleListFilter):
    """Filter MycoBank records by publication decade."""
    title = '📅 Publication Decade'
    parameter_name = 'decade'

    def lookups(self, request, model_admin):
        # Pre-defined meaningful decade ranges for fungi taxonomy
        return [
            ('2020', '🔬 2020s (Modern)'),
            ('2010', '📊 2010s'),
            ('2000', '💻 2000s'),
            ('1990', '📚 1990s'),
            ('1980', '🔍 1980s'),
            ('1970', '📖 1970s'),
            ('1900', '📜 Early 1900s (1900-1969)'),
            ('1800', '🏛️ 1800s (Historical)'),
            ('pre1800', '⏳ Pre-1800 (Classical)'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == '2020':
            return queryset.filter(year__gte='2020')
        elif value == '2010':
            return queryset.filter(year__gte='2010', year__lt='2020')
        elif value == '2000':
            return queryset.filter(year__gte='2000', year__lt='2010')
        elif value == '1990':
            return queryset.filter(year__gte='1990', year__lt='2000')
        elif value == '1980':
            return queryset.filter(year__gte='1980', year__lt='1990')
        elif value == '1970':
            return queryset.filter(year__gte='1970', year__lt='1980')
        elif value == '1900':
            return queryset.filter(year__gte='1900', year__lt='1970')
        elif value == '1800':
            return queryset.filter(year__gte='1800', year__lt='1900')
        elif value == 'pre1800':
            return queryset.filter(year__lt='1800')
        return queryset


class CandidateQualityFilter(admin.SimpleListFilter):
    """Filter by quality of MycoBank candidates."""
    title = '🏆 Candidate Quality'
    parameter_name = 'candidate_quality'

    def lookups(self, request, model_admin):
        return [
            ('has_candidate', '✅ Has MycoBank Candidate'),
            ('no_candidate', '❌ No Candidate Found'),
            ('high_confidence', '🎯 High Confidence (≥90%)'),
            ('medium_confidence', '📊 Medium Confidence (70-89%)'),
            ('low_confidence', '⚠️ Low Confidence (<70%)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'has_candidate':
            return queryset.exclude(mycobank_id__isnull=True)
        elif self.value() == 'no_candidate':
            return queryset.filter(mycobank_id__isnull=True)
        elif self.value() == 'high_confidence':
            return queryset.filter(
                Q(org_score__gte=90) | Q(conf_score__gte=90) | Q(foray_score__gte=90)
            ).exclude(mycobank_id__isnull=True)
        elif self.value() == 'medium_confidence':
            return queryset.filter(
                (Q(org_score__gte=70) & Q(org_score__lt=90)) |
                (Q(conf_score__gte=70) & Q(conf_score__lt=90)) |
                (Q(foray_score__gte=70) & Q(foray_score__lt=90))
            ).exclude(
                Q(org_score__gte=90) | Q(conf_score__gte=90) | Q(foray_score__gte=90)
            ).exclude(mycobank_id__isnull=True)
        elif self.value() == 'low_confidence':
            return queryset.filter(
                org_score__lt=70,
                conf_score__lt=70,
                foray_score__lt=70
            ).exclude(mycobank_id__isnull=True)
        return queryset


class ForayCollectionFilter(admin.SimpleListFilter):
    """Filter Foray records by collection series and specimen ranges."""
    title = '🍄 Collection Series'
    parameter_name = 'collection_series'

    def lookups(self, request, model_admin):
        # Get unique collection prefixes from foray_id values
        foray_ids = ForayFungi2023.objects.values_list('foray_id', flat=True)
        
        # Extract collection series (everything before the last hyphen and number)
        series = set()
        for foray_id in foray_ids:
            if '-' in foray_id:
                # Extract series like "CMS23A" from "CMS23A-001"
                prefix = foray_id.rsplit('-', 1)[0]
                series.add(prefix)
        
        # Sort and create lookup options
        series = sorted(series)
        lookups = []
        
        for serie in series[:10]:  # Limit to 10 most common series
            lookups.append((serie, f'🔬 {serie} Series'))
        
        # Add range-based options
        lookups.extend([
            ('001-050', '📊 Specimens 001-050'),
            ('051-100', '📊 Specimens 051-100'),
            ('101-200', '📊 Specimens 101-200'),
            ('201+', '📊 Specimens 201+'),
        ])
        
        return lookups

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
            
        if value in ['001-050', '051-100', '101-200', '201+']:
            # Filter by specimen number ranges
            if value == '001-050':
                return queryset.filter(foray_id__regex=r'-0[0-4][0-9]$|^.*-050$')
            elif value == '051-100':
                return queryset.filter(foray_id__regex=r'-0[5-9][0-9]$|^.*-100$')
            elif value == '101-200':
                return queryset.filter(foray_id__regex=r'-1[0-9][0-9]$|^.*-200$')
            elif value == '201+':
                return queryset.filter(foray_id__regex=r'-[2-9][0-9][0-9]$')
        else:
            # Filter by collection series prefix
            return queryset.filter(foray_id__startswith=value + '-')
        
        return queryset


# ---------------------------------------------------------------------------
# Source Data Administration
# ---------------------------------------------------------------------------

@admin.register(ForayFungi2023)
class ForayFungi2023Admin(admin.ModelAdmin):
    """Enhanced admin for Foray 2023 fungi observations."""
    
    list_display = (
        'foray_id', 
        'display_org_entry', 
        'display_conf_name', 
        'display_foray_name',
        'name_consistency',
        'has_matches'
    )
    list_filter = (
        ForayCollectionFilter,
        NameConsistencyFilter,
        MatchingStatusFilter,
    )
    search_fields = (
        'foray_id', 
        'genus_and_species_org_entry', 
        'genus_and_species_conf', 
        'genus_and_species_foray_name'
    )
    ordering = ('foray_id',)
    readonly_fields = ('name_consistency', 'matching_results')
    
    fieldsets = (
        ('Identification', {
            'fields': ('foray_id',)
        }),
        ('Name Variants', {
            'fields': (
                'genus_and_species_org_entry',
                'genus_and_species_conf', 
                'genus_and_species_foray_name'
            ),
            'description': 'Three name variants for this fungi specimen'
        }),
        ('Analysis', {
            'fields': ('name_consistency', 'matching_results'),
            'classes': ('collapse',),
            'description': 'Computed analysis and matching results'
        }),
    )

    def display_org_entry(self, obj):
        """Display original entry with truncation."""
        name = obj.genus_and_species_org_entry or '—'
        return name[:50] + ('...' if len(name) > 50 else '')
    display_org_entry.short_description = '📝 Original Entry'

    def display_conf_name(self, obj):
        """Display conference name with truncation."""
        name = obj.genus_and_species_conf or '—'
        return name[:50] + ('...' if len(name) > 50 else '')
    display_conf_name.short_description = '🎓 Conference Name'

    def display_foray_name(self, obj):
        """Display foray name with truncation."""
        name = obj.genus_and_species_foray_name or '—'
        return name[:50] + ('...' if len(name) > 50 else '')
    display_foray_name.short_description = '🍄 Foray Name'

    def name_consistency(self, obj):
        """Show consistency between the three names."""
        names = [
            obj.genus_and_species_org_entry or '',
            obj.genus_and_species_conf or '', 
            obj.genus_and_species_foray_name or ''
        ]
        
        if all(n == names[0] for n in names):
            return mark_safe('✅ <strong style="color: green;">All Match</strong>')
        elif len(set(names)) == 2:
            return mark_safe('⚠️ <strong style="color: orange;">Partial Match</strong>')
        else:
            return mark_safe('❌ <strong style="color: red;">All Different</strong>')
    name_consistency.short_description = 'Name Consistency'

    def has_matches(self, obj):
        """Check if this record has any matches."""
        from .models import ForayMatch
        if ForayMatch.objects.filter(foray_id=obj.foray_id).exists():
            return mark_safe('✅ <strong style="color: green;">Has Matches</strong>')
        return mark_safe('❌ <span style="color: red;">No Matches</span>')
    has_matches.short_description = 'Matching Status'

    def matching_results(self, obj):
        """Show detailed matching results."""
        from .models import ForayMatch, ForayPerfectMycoMatch, ForayMismatchMycoScores
        
        results = []
        
        # Check for perfect matches
        perfect = ForayPerfectMycoMatch.objects.filter(foray_id=obj.foray_id).first()
        if perfect:
            results.append(f'🎯 <strong>Perfect Match:</strong> {perfect.mycobank_name} ({perfect.mycobank_id})')
        
        # Check for mismatch scores
        scores = ForayMismatchMycoScores.objects.filter(foray_id=obj.foray_id).first()
        if scores:
            results.append(f'📊 <strong>Best Scores:</strong> Org: {scores.org_score}%, Conf: {scores.conf_score}%, Foray: {scores.foray_score}%')
            if scores.mycobank_name:
                results.append(f'🔗 <strong>Best Candidate:</strong> {scores.mycobank_name} ({scores.mycobank_id})')
        
        return mark_safe('<br>'.join(results) if results else 'No matching results found')
    matching_results.short_description = 'Matching Results'


@admin.register(MycoBankList)
class MycoBankListAdmin(admin.ModelAdmin):
    """Enhanced admin for MycoBank taxonomic database."""
    
    list_display = (
        'mycobank_id', 
        'display_preferred_name',
        'display_taxon_name',
        'display_current_name', 
        'authors',
        'year',
        'has_hyperlink'
    )
    list_filter = (
        PublicationDecadeFilter,
        MycoBankCompleteness,
    )
    search_fields = (
        'mycobank_id', 
        'taxon_name', 
        'current_name', 
        'authors'
    )
    ordering = ('mycobank_id',)
    readonly_fields = ('preferred_name_display', 'hyperlink_display')
    
    fieldsets = (
        ('Identification', {
            'fields': ('mycobank_id', 'preferred_name_display')
        }),
        ('Taxonomic Names', {
            'fields': ('taxon_name', 'current_name'),
            'description': 'Original taxonomic name and current accepted name'
        }),
        ('Publication Details', {
            'fields': ('authors', 'year'),
        }),
        ('Reference', {
            'fields': ('hyperlink', 'hyperlink_display'),
            'classes': ('collapse',),
        }),
    )

    def display_preferred_name(self, obj):
        """Display preferred name with emphasis."""
        name = obj.preferred_name
        return format_html('<strong>{}</strong>', name[:60] + ('...' if len(name) > 60 else ''))
    display_preferred_name.short_description = '🏷️ Preferred Name'

    def display_taxon_name(self, obj):
        """Display taxon name."""
        name = obj.taxon_name or '—'
        return name[:50] + ('...' if len(name) > 50 else '')
    display_taxon_name.short_description = '📜 Taxon Name'

    def display_current_name(self, obj):
        """Display current name."""
        name = obj.current_name or '—'
        if name != '—' and name != (obj.taxon_name or ''):
            return format_html('<span style="color: blue;">{}</span>', name[:50] + ('...' if len(name) > 50 else ''))
        return name[:50] + ('...' if len(name) > 50 else '')
    display_current_name.short_description = '🔄 Current Name'

    def has_hyperlink(self, obj):
        """Check if record has hyperlink."""
        return '🔗' if obj.hyperlink else '—'
    has_hyperlink.short_description = 'Link'

    def preferred_name_display(self, obj):
        """Show which name is being used as preferred."""
        if obj.current_name and obj.current_name.strip():
            return mark_safe(f'<strong>{obj.preferred_name}</strong> <em>(using current name)</em>')
        return mark_safe(f'<strong>{obj.preferred_name}</strong> <em>(using taxon name)</em>')
    preferred_name_display.short_description = 'Preferred Name Logic'

    def hyperlink_display(self, obj):
        """Display clickable hyperlink."""
        if obj.hyperlink:
            return format_html('<a href="{}" target="_blank">🔗 Open in MycoBank</a>', obj.hyperlink)
        return '—'
    hyperlink_display.short_description = 'Reference Link'


# ---------------------------------------------------------------------------
# Matching Results Administration
# ---------------------------------------------------------------------------

@admin.register(ForayMatch)
class ForayMatchAdmin(admin.ModelAdmin):
    """Enhanced admin for unified match results."""
    
    list_display = (
        'foray_id',
        'match_category_display', 
        'display_org_entry',
        'display_conf_name', 
        'display_foray_name',
        'view_details'
    )
    list_filter = ('match_category',)
    search_fields = ('foray_id', 'org_entry', 'conf_name', 'foray_name')
    ordering = ('foray_id',)
    readonly_fields = ('detailed_analysis',)

    fieldsets = (
        ('Identification', {
            'fields': ('foray_id', 'match_category')
        }),
        ('Name Variants', {
            'fields': ('org_entry', 'conf_name', 'foray_name'),
        }),
        ('Analysis', {
            'fields': ('detailed_analysis',),
            'classes': ('collapse',),
        }),
    )

    def match_category_display(self, obj):
        """Display match category with color coding."""
        category_colors = {
            'ALL_MATCH': 'green',
            'ORG_CONF_MATCH': 'orange',
            'ORG_FORAY_MATCH': 'orange', 
            'CONF_FORAY_MATCH': 'orange',
            'ALL_DIFFERENT': 'red'
        }
        color = category_colors.get(obj.match_category, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.match_category)
    match_category_display.short_description = '🎯 Match Category'

    def display_org_entry(self, obj):
        return obj.org_entry[:40] + ('...' if len(obj.org_entry) > 40 else '')
    display_org_entry.short_description = '📝 Original'

    def display_conf_name(self, obj):
        return obj.conf_name[:40] + ('...' if len(obj.conf_name) > 40 else '')
    display_conf_name.short_description = '🎓 Conference'

    def display_foray_name(self, obj):
        return obj.foray_name[:40] + ('...' if len(obj.foray_name) > 40 else '')
    display_foray_name.short_description = '🍄 Foray'

    def view_details(self, obj):
        """Link to view detailed matching information."""
        return format_html('<a href="/admin/core/foraymismatchmycoscores/?foray_id__exact={}">📊 View Scores</a>', obj.foray_id)
    view_details.short_description = 'Details'

    def detailed_analysis(self, obj):
        """Show comprehensive matching analysis."""
        from .models import ForayPerfectMycoMatch, ForayMismatchMycoScores, ReviewedMatch
        
        analysis = []
        analysis.append(f'<h3>Foray ID: {obj.foray_id}</h3>')
        analysis.append(f'<p><strong>Category:</strong> {obj.match_category}</p>')
        
        # Show name comparison
        analysis.append('<h4>Name Comparison:</h4>')
        analysis.append(f'<ul>')
        analysis.append(f'<li><strong>Original Entry:</strong> "{obj.org_entry}"</li>')
        analysis.append(f'<li><strong>Conference Name:</strong> "{obj.conf_name}"</li>')
        analysis.append(f'<li><strong>Foray Name:</strong> "{obj.foray_name}"</li>')
        analysis.append(f'</ul>')
        
        # Check for MycoBank matches
        perfect_match = ForayPerfectMycoMatch.objects.filter(foray_id=obj.foray_id).first()
        if perfect_match:
            analysis.append('<h4>🎯 Perfect MycoBank Match:</h4>')
            analysis.append(f'<p><strong>MycoBank ID:</strong> {perfect_match.mycobank_id}</p>')
            analysis.append(f'<p><strong>Name:</strong> {perfect_match.mycobank_name}</p>')
        
        # Check for similarity scores
        scores = ForayMismatchMycoScores.objects.filter(foray_id=obj.foray_id).first()
        if scores:
            analysis.append('<h4>📊 Similarity Scores:</h4>')
            analysis.append(f'<ul>')
            analysis.append(f'<li>Original Entry: <strong>{scores.org_score}%</strong></li>')
            analysis.append(f'<li>Conference Name: <strong>{scores.conf_score}%</strong></li>')
            analysis.append(f'<li>Foray Name: <strong>{scores.foray_score}%</strong></li>')
            analysis.append(f'</ul>')
            
            if scores.mycobank_name:
                analysis.append('<h4>🏆 Best Candidate:</h4>')
                analysis.append(f'<p><strong>MycoBank ID:</strong> {scores.mycobank_id}</p>')
                analysis.append(f'<p><strong>Name:</strong> {scores.mycobank_name}</p>')
                analysis.append(f'<p><strong>Match Type:</strong> {scores.mycobank_expl}</p>')
        
        # Check review status
        review = ReviewedMatch.objects.filter(foray_id=obj.foray_id).first()
        if review:
            analysis.append('<h4>👤 Review Status:</h4>')
            analysis.append(f'<p><strong>Status:</strong> {review.status}</p>')
            analysis.append(f'<p><strong>Validated Name:</strong> {review.validated_name or "Not set"}</p>')
            analysis.append(f'<p><strong>Reviewer:</strong> {review.reviewer_name or "Not set"}</p>')
            analysis.append(f'<p><strong>Reviewed:</strong> {review.reviewed_at}</p>')
        
        return mark_safe(''.join(analysis))
    detailed_analysis.short_description = 'Detailed Analysis'


@admin.register(ForayPerfectMatch)
class ForayPerfectMatchAdmin(admin.ModelAdmin):
    """Admin for perfect internal matches."""
    
    list_display = ('foray_id', 'name', 'has_mycobank_match')
    search_fields = ('foray_id', 'name')
    ordering = ('foray_id',)

    def has_mycobank_match(self, obj):
        """Check if this has a corresponding MycoBank match."""
        from .models import ForayPerfectMycoMatch
        if ForayPerfectMycoMatch.objects.filter(foray_id=obj.foray_id).exists():
            return mark_safe('✅ <span style="color: green;">Yes</span>')
        return mark_safe('❌ <span style="color: red;">No</span>')
    has_mycobank_match.short_description = 'MycoBank Match'


@admin.register(ForayPerfectMycoMatch)
class ForayPerfectMycoMatchAdmin(admin.ModelAdmin):
    """Admin for perfect matches with MycoBank."""
    
    list_display = (
        'foray_id', 
        'mycobank_link',
        'mycobank_name',
        'view_mycobank'
    )
    search_fields = ('foray_id', 'mycobank_id', 'mycobank_name')
    ordering = ('foray_id',)

    def mycobank_link(self, obj):
        """Display MycoBank ID as a link."""
        return format_html('<strong>{}</strong>', obj.mycobank_id)
    mycobank_link.short_description = '🆔 MycoBank ID'

    def view_mycobank(self, obj):
        """Link to view the MycoBank record."""
        try:
            url = reverse('admin:core_mycobanklist_change', args=[obj.mycobank_id])
            return format_html('<a href="{}">🔍 View Record</a>', url)
        except:
            return '—'
    view_mycobank.short_description = 'MycoBank Record'


@admin.register(ForayMismatchExplanation)
class ForayMismatchExplanationAdmin(admin.ModelAdmin):
    """Admin for mismatch explanations."""
    
    list_display = (
        'foray_id',
        'explanation_display',
        'display_org_entry', 
        'display_conf_name',
        'display_foray_name'
    )
    list_filter = ('explanation',)
    search_fields = ('foray_id', 'org_entry', 'conf_name', 'foray_name')
    ordering = ('foray_id',)

    def explanation_display(self, obj):
        """Display explanation with color coding."""
        colors = {
            'ORG_CONF_MATCH': 'blue',
            'ORG_FORAY_MATCH': 'blue', 
            'CONF_FORAY_MATCH': 'blue',
            'ALL_DIFFERENT': 'red'
        }
        color = colors.get(obj.explanation, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.explanation)
    explanation_display.short_description = '📋 Explanation'

    def display_org_entry(self, obj):
        return obj.org_entry[:35] + ('...' if len(obj.org_entry) > 35 else '')
    display_org_entry.short_description = '📝 Original'

    def display_conf_name(self, obj):
        return obj.conf_name[:35] + ('...' if len(obj.conf_name) > 35 else '')
    display_conf_name.short_description = '🎓 Conference'

    def display_foray_name(self, obj):
        return obj.foray_name[:35] + ('...' if len(obj.foray_name) > 35 else '')
    display_foray_name.short_description = '🍄 Foray'


@admin.register(ForayMismatchMycoScores)
class ForayMismatchMycoScoresAdmin(admin.ModelAdmin):
    """Enhanced admin for similarity scores and candidates."""
    
    list_display = (
        'foray_id',
        'score_summary',
        'best_candidate',
        'match_explanation',
        'view_mycobank'
    )
    list_filter = (
        'mycobank_expl',
        ScoreRangeFilter,
        CandidateQualityFilter,
    )
    search_fields = ('foray_id', 'mycobank_id', 'mycobank_name')
    ordering = ('foray_id',)
    readonly_fields = ('score_analysis', 'candidate_details')

    fieldsets = (
        ('Identification', {
            'fields': ('foray_id',)
        }),
        ('Similarity Scores', {
            'fields': ('org_score', 'conf_score', 'foray_score', 'score_analysis'),
            'description': 'Fuzzy string matching scores (0-100%)'
        }),
        ('Best MycoBank Candidate', {
            'fields': ('mycobank_id', 'mycobank_name', 'mycobank_expl', 'candidate_details'),
            'classes': ('collapse',),
        }),
    )

    def score_summary(self, obj):
        """Display scores with color coding."""
        max_score = max(obj.org_score, obj.conf_score, obj.foray_score)
        
        def score_color(score):
            if score >= 90: return 'green'
            elif score >= 70: return 'orange'
            else: return 'red'
        
        return format_html(
            'O:<span style="color: {};">{:.0f}%</span> | '
            'C:<span style="color: {};">{:.0f}%</span> | '
            'F:<span style="color: {};">{:.0f}%</span>',
            score_color(obj.org_score), obj.org_score,
            score_color(obj.conf_score), obj.conf_score,
            score_color(obj.foray_score), obj.foray_score
        )
    score_summary.short_description = '📊 Scores (O/C/F)'

    def best_candidate(self, obj):
        """Display best MycoBank candidate."""
        if obj.mycobank_name:
            return format_html('<strong>{}</strong> ({})', obj.mycobank_name[:40] + ('...' if len(obj.mycobank_name) > 40 else ''), obj.mycobank_id)
        return '—'
    best_candidate.short_description = '🏆 Best Candidate'

    def match_explanation(self, obj):
        """Display match explanation with formatting."""
        if obj.mycobank_expl:
            return format_html('<code>{}</code>', obj.mycobank_expl)
        return '—'
    match_explanation.short_description = '🔍 Match Type'

    def view_mycobank(self, obj):
        """Link to MycoBank record."""
        if obj.mycobank_id:
            try:
                url = reverse('admin:core_mycobanklist_change', args=[obj.mycobank_id])
                return format_html('<a href="{}">🔍 View</a>', url)
            except:
                return '—'
        return '—'
    view_mycobank.short_description = 'MycoBank'

    def score_analysis(self, obj):
        """Detailed score analysis."""
        scores = [
            ('Original Entry', obj.org_score),
            ('Conference Name', obj.conf_score), 
            ('Foray Name', obj.foray_score)
        ]
        
        analysis = ['<h4>Score Breakdown:</h4><ul>']
        for name, score in scores:
            quality = 'Excellent' if score >= 90 else 'Good' if score >= 70 else 'Poor'
            color = 'green' if score >= 90 else 'orange' if score >= 70 else 'red'
            analysis.append(f'<li><strong>{name}:</strong> <span style="color: {color};">{score:.1f}% ({quality})</span></li>')
        analysis.append('</ul>')
        
        best_score = max(scores, key=lambda x: x[1])
        analysis.append(f'<p><strong>Best Match:</strong> {best_score[0]} ({best_score[1]:.1f}%)</p>')
        
        return mark_safe(''.join(analysis))
    score_analysis.short_description = 'Score Analysis'

    def candidate_details(self, obj):
        """Show candidate details with MycoBank link."""
        if not obj.mycobank_id:
            return 'No candidate selected'
        
        details = []
        details.append(f'<h4>Candidate Information:</h4>')
        details.append(f'<p><strong>MycoBank ID:</strong> {obj.mycobank_id}</p>')
        details.append(f'<p><strong>Name:</strong> {obj.mycobank_name}</p>')
        details.append(f'<p><strong>Match Explanation:</strong> {obj.mycobank_expl}</p>')
        
        # Try to get additional MycoBank details
        try:
            from .models import MycoBankList
            myco_record = MycoBankList.objects.get(mycobank_id=obj.mycobank_id)
            details.append(f'<p><strong>Authors:</strong> {myco_record.authors or "Not available"}</p>')
            details.append(f'<p><strong>Year:</strong> {myco_record.year or "Not available"}</p>')
            if myco_record.hyperlink:
                details.append(f'<p><strong>Reference:</strong> <a href="{myco_record.hyperlink}" target="_blank">View in MycoBank</a></p>')
        except:
            pass
        
        return mark_safe(''.join(details))
    candidate_details.short_description = 'Candidate Details'


# ---------------------------------------------------------------------------
# Review Workflow Administration  
# ---------------------------------------------------------------------------

@admin.register(ReviewedMatch)
class ReviewedMatchAdmin(admin.ModelAdmin):
    """Enhanced admin for review workflow."""
    
    list_display = (
        'foray_id',
        'status_display',
        'validated_name_display',
        'reviewer_name',
        'reviewed_at',
        'view_original'
    )
    list_filter = ('status', 'reviewer_name')
    search_fields = ('foray_id', 'validated_name', 'reviewer_name')
    ordering = ('-reviewed_at',)
    date_hierarchy = 'reviewed_at'

    fieldsets = (
        ('Identification', {
            'fields': ('foray_id', 'status')
        }),
        ('Original Names', {
            'fields': ('org_entry', 'conf_name', 'foray_name'),
            'description': 'Original name variants from Foray data'
        }),
        ('Review Result', {
            'fields': ('validated_name', 'reviewer_name'),
        }),
        ('Metadata', {
            'fields': ('reviewed_at',),
            'classes': ('collapse',),
        }),
    )

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'REVIEWED': 'green',
            'PENDING': 'orange',
            'SKIPPED': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    status_display.short_description = '📋 Status'

    def validated_name_display(self, obj):
        """Display validated name with emphasis."""
        if obj.validated_name:
            return format_html('<strong style="color: green;">{}</strong>', obj.validated_name)
        return mark_safe('<em style="color: gray;">Not set</em>')
    validated_name_display.short_description = '✅ Validated Name'

    def view_original(self, obj):
        """Link to view original Foray record."""
        try:
            url = reverse('admin:core_forayfungi2023_change', args=[obj.foray_id])
            return format_html('<a href="{}">🔍 View Original</a>', url)
        except:
            return '—'
    view_original.short_description = 'Original Record'
