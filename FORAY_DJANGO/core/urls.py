from django.urls import path
from . import views

# Optional: namespace your URLs (use as "core:detail", etc.)
app_name = "core"

urlpatterns = [
    # ---------- Dashboard ----------
    path("", views.dashboard, name="dashboard"),

    # ---------- Matching UI ----------
    path("matches/", views.match_browser, name="match_browser"),
    path("detail/<str:foray_id>/", views.detail, name="detail"),

    # ---------- Review workflow ----------
    path("review/", views.review_next, name="review_next"),                   # queue (supports ?foray_id=...)
    path("reviewed/", views.view_reviewed, name="view_reviewed"),             # list of Reviewed/Pending/Skipped
    path("reviewed/reset/<str:foray_id>/", views.reviewed_reset,              # POST: send back to review (soft reset)
         name="reviewed_reset"),

    # ---------- MycoBank pages ----------
    path("myco/perfect/", views.myco_perfect, name="myco_perfect"),
    path("myco/mismatch/", views.myco_mismatch, name="myco_mismatch"),
]
