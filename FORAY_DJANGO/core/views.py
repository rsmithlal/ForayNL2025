from __future__ import annotations

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
import csv

from core.forms import ReviewForm
from core.models import (
    ForayFungi2023,
    ForayMatch,
    ForayMismatchExplanation,
    ForayMismatchMycoScores,
    ForayPerfectMatch,
    ForayPerfectMycoMatch,
    MycoBankList,
    ReviewedMatch,
)

MATCH_CATEGORY_ALIAS = {
    "PERFECT": "ALL_MATCH",
    "MATCH_ORG_CONF": "MATCH_ORG_CONF",
    "MATCH_ORG_FORAY": "MATCH_ORG_FORAY",
    "MATCH_CONF_FORAY": "MATCH_CONF_FORAY",
    "ALL_DIFFERENT": "ALL_DIFFERENT",
}

def _friendly_pairs(explanation: str | None) -> list[str]:
    exp = (explanation or "").upper()
    if exp == "ORG_CONF_MATCH": return ["ORG ↔ CONF"]
    if exp == "ORG_FORAY_MATCH": return ["ORG ↔ FORAY"]
    if exp == "CONF_FORAY_MATCH": return ["CONF ↔ FORAY"]
    if exp == "ALL_DIFFERENT": return ["ALL DIFFERENT"]
    return []

def _myco_candidate_for_foray(foray_id: str):
    s = ForayMismatchMycoScores.objects.filter(foray_id=foray_id).first()
    if s and getattr(s, "mycobank_id", None):
        return MycoBankList.objects.filter(mycobank_id=s.mycobank_id).first()
    return None

# ---------------- Dashboard ----------------
def dashboard(request):
    return render(request, "core/dashboard.html")

# ---------------- Match Browser ----------------
def match_browser(request):
    match_category = request.GET.get("match_category", "ALL")
    search_term = (request.GET.get("search") or "").strip()

    qs = ForayMatch.objects.all().order_by("foray_id")
    effective = MATCH_CATEGORY_ALIAS.get(match_category, match_category)
    if effective != "ALL":
        qs = qs.filter(match_category=effective)
    if search_term:
        qs = qs.filter(
            Q(foray_id__icontains=search_term)
            | Q(org_entry__icontains=search_term)
            | Q(conf_name__icontains=search_term)
            | Q(foray_name__icontains=search_term)
        )
    if "export" in request.GET:
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="filtered_foray_matches.csv"'
        w = csv.writer(resp)
        w.writerow(["Foray ID", "Org Entry", "Conf Name", "Foray Name", "Match Category"])
        for item in qs:
            w.writerow([item.foray_id, item.org_entry, item.conf_name, item.foray_name, item.match_category])
        return resp

    return render(request, "core/match_browser.html", {
        "matches": qs, "selected_category": match_category, "search": search_term
    })

# ---------------- Review Flow ----------------
def review_next(request):
    foray_id = request.GET.get("foray_id")
    if foray_id:
        record = get_object_or_404(ForayMismatchExplanation, foray_id=foray_id)
    else:
        reviewed_ids = list(ReviewedMatch.objects.values_list("foray_id", flat=True))
        record = ForayMismatchExplanation.objects.exclude(foray_id__in=reviewed_ids).first()
        if not record:
            return render(request, "core/review_done.html")

    myco_scores = ForayMismatchMycoScores.objects.filter(foray_id=record.foray_id).first()
    myco_perfect = ForayPerfectMycoMatch.objects.filter(foray_id=record.foray_id).first()
    myco_candidate = _myco_candidate_for_foray(record.foray_id)

    try:
        reviewed = ReviewedMatch.objects.get(foray_id=record.foray_id)
        form = ReviewForm(initial={
            "validated_name": reviewed.validated_name,
            "reviewer_name": reviewed.reviewer_name,
            "status": reviewed.status or "REVIEWED",
        })
    except ReviewedMatch.DoesNotExist:
        form = ReviewForm()

    if request.method == "POST":
        pressed_skip = "skip" in request.POST
        pressed_save_next = "save_next" in request.POST

        if pressed_skip:
            ReviewedMatch.objects.update_or_create(
                foray_id=record.foray_id,
                defaults={
                    "org_entry": record.org_entry,
                    "conf_name": record.conf_name,
                    "foray_name": record.foray_name,
                    "validated_name": "",
                    "reviewer_name": request.POST.get("reviewer_name") or None,
                    "status": "PENDING",
                },
            )
            return redirect("review_next")

        form = ReviewForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data.get("status") or "REVIEWED"
            ReviewedMatch.objects.update_or_create(
                foray_id=record.foray_id,
                defaults={
                    "org_entry": record.org_entry,
                    "conf_name": record.conf_name,
                    "foray_name": record.foray_name,
                    "validated_name": form.cleaned_data["validated_name"],
                    "reviewer_name": form.cleaned_data["reviewer_name"],
                    "status": status,
                },
            )
            if pressed_save_next:
                return redirect("review_next")

    total = ForayMismatchExplanation.objects.count()
    reviewed_count = ReviewedMatch.objects.filter(status="REVIEWED").count()
    percent = int((reviewed_count / total) * 100) if total else 0

    return render(request, "core/review_form.html", {
        "record": record, "form": form,
        "myco_scores": myco_scores, "myco_perfect": myco_perfect,
        "myco_candidate": myco_candidate,
        "pairs": _friendly_pairs(record.explanation),
        "total": total, "reviewed": reviewed_count, "percent": percent,
    })

def view_reviewed(request):
    status = (request.GET.get("status") or "ALL").upper()
    qs = ReviewedMatch.objects.all().order_by("-reviewed_at")
    if status in ("REVIEWED", "PENDING", "SKIPPED"):
        qs = qs.filter(status=status)
    return render(request, "core/view_reviewed.html", {"reviews": qs, "status": status})

@require_POST
def reviewed_reset(request, foray_id: str):
    obj, _ = ReviewedMatch.objects.get_or_create(foray_id=foray_id)
    obj.status = "PENDING"
    obj.validated_name = ""
    obj.reviewer_name = None
    obj.save()
    messages.success(request, f"{foray_id} was sent back to review.")
    return redirect("view_reviewed")

# ---------------- Detail ----------------
def detail(request, foray_id):
    rid = str(foray_id).strip()
    result = (
        ForayPerfectMycoMatch.objects.filter(foray_id=rid).first()
        or ForayPerfectMatch.objects.filter(foray_id=rid).first()
        or ForayMismatchExplanation.objects.filter(foray_id=rid).first()
    )
    foray = list(ForayFungi2023.objects.filter(foray_id=rid).values())

    myco = []
    myco_id = getattr(result, "mycobank_id", None) if result else None
    if myco_id:
        myco = list(MycoBankList.objects.filter(mycobank_id=str(myco_id).strip()).values())
    if not myco:
        cand = _myco_candidate_for_foray(rid)
        if cand:
            myco = [MycoBankList.objects.filter(mycobank_id=cand.mycobank_id).values().first()]

    result_dict = {}
    if result:
        if isinstance(result, ForayPerfectMycoMatch):
            result_dict = {"Foray_ID": result.foray_id, "MycoBank_ID": result.mycobank_id,
                           "Name": getattr(result, "mycobank_name", ""), "Explanation": "",
                           "Match_Category": "PERFECT_MYCOBANK"}
        elif isinstance(result, ForayPerfectMatch):
            result_dict = {"Foray_ID": result.foray_id, "MycoBank_ID": "",
                           "Name": getattr(result, "name", ""), "Explanation": "",
                           "Match_Category": "PERFECT"}
        else:
            result_dict = {"Foray_ID": result.foray_id, "MycoBank_ID": "",
                           "Name": getattr(result, "foray_name", "")
                                   or getattr(result, "org_entry", "")
                                   or getattr(result, "conf_name", ""),
                           "Explanation": getattr(result, "explanation", ""),
                           "Match_Category": "MISMATCH"}

    return render(request, "core/detail.html", {"result": result_dict, "foray": foray, "myco": myco})

# ---------------- MycoBank pages ----------------
def myco_perfect(request):
    search = (request.GET.get("search") or "").strip()
    qs = ForayPerfectMycoMatch.objects.all().order_by("foray_id")
    if search:
        qs = qs.filter(
            Q(foray_id__icontains=search)
            | Q(mycobank_id__icontains=search)
            | Q(mycobank_name__icontains=search)
        )
    foray_map = {
        r["foray_id"]: r
        for r in ForayFungi2023.objects.filter(
            foray_id__in=list(qs.values_list("foray_id", flat=True))
        ).values("foray_id", "genus_and_species_org_entry", "genus_and_species_conf", "genus_and_species_foray_name")
    }
    rows = []
    for m in qs:
        f = foray_map.get(m.foray_id, {})
        rows.append({
            "foray_id": m.foray_id, "mycobank_id": m.mycobank_id, "mycobank_name": m.mycobank_name,
            "org_entry": f.get("genus_and_species_org_entry", ""),
            "conf_name": f.get("genus_and_species_conf", ""),
            "foray_name": f.get("genus_and_species_foray_name", ""),
        })
    return render(request, "core/myco_perfect.html", {"rows": rows, "search": search})

def myco_mismatch(request):
    search = (request.GET.get("search") or "").strip()
    scores_qs = ForayMismatchMycoScores.objects.all().order_by("foray_id")
    if search:
        scores_qs = scores_qs.filter(foray_id__icontains=search)
    expl_by_id = {
        r["foray_id"]: r
        for r in ForayMismatchExplanation.objects.filter(
            foray_id__in=list(scores_qs.values_list("foray_id", flat=True))
        ).values("foray_id", "org_entry", "conf_name", "foray_name", "explanation")
    }
    try:
        myco_ids = [mid for mid in scores_qs.values_list("mycobank_id", flat=True) if mid]
    except Exception:
        myco_ids = []
    myco_map = {m.mycobank_id: m for m in MycoBankList.objects.filter(mycobank_id__in=myco_ids)} if myco_ids else {}
    rows = []
    for s in scores_qs:
        meta = expl_by_id.get(s.foray_id, {})
        s_mb_id = getattr(s, "mycobank_id", None)
        s_mb_name = getattr(s, "mycobank_name", None)
        mb_obj = myco_map.get(s_mb_id) if s_mb_id else None
        if s_mb_name:
            mb_name = s_mb_name
        elif mb_obj:
            mb_name = getattr(mb_obj, "current_name", None) or getattr(mb_obj, "taxon_name", "") or ""
        else:
            mb_name = ""
        rows.append({
            "foray_id": s.foray_id,
            "org_entry": meta.get("org_entry", ""),
            "conf_name": meta.get("conf_name", ""),
            "foray_name": meta.get("foray_name", ""),
            "explanation": meta.get("explanation", ""),
            "org_score": getattr(s, "org_score", None),
            "conf_score": getattr(s, "conf_score", None),
            "foray_score": getattr(s, "foray_score", None),
            "mycobank_name": mb_name,
            "mycobank_expl": getattr(s, "mycobank_expl", ""),
        })
    return render(request, "core/myco_mismatch.html", {"rows": rows, "search": search})
