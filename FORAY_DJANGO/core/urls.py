from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("matches/", views.match_browser, name="match_browser"),
    path("detail/<str:foray_id>/", views.detail, name="detail"),
    path("review/", views.review_next, name="review_next"),
    path("reviewed/", views.view_reviewed, name="view_reviewed"),
    path("reviewed/reset/<str:foray_id>/", views.reviewed_reset, name="reviewed_reset"),
    path("myco/perfect/", views.myco_perfect, name="myco_perfect"),
    path("myco/mismatch/", views.myco_mismatch, name="myco_mismatch"),
]
