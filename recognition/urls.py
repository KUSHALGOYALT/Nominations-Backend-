from django.urls import path
from . import views

# Results (vote_counts, winners, none_of_above_count) are returned only by GET session when phase is results/closed. No separate /results endpoint.
urlpatterns = [
    path("auth/check", views.admin_check),
    path("qr-join", views.qr_join),
    path("session", views.session_get),
    path("session/create", views.session_create),
    path("session/patch", views.session_patch),
    path("nominations", views.nominations_list),
    path("nominations/create", views.nomination_create),
    path("nominations/<int:nomination_id>/delete", views.nomination_delete),
    path("votes/create", views.vote_create),
]
