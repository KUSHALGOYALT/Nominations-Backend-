from django.urls import path
from . import views

urlpatterns = [
    path("auth/check", views.admin_check),
    path("session", views.session_get),
    path("session/create", views.session_create),
    path("session/patch", views.session_patch),
    path("nominations", views.nominations_list),
    path("nominations/create", views.nomination_create),
    path("nominations/<int:nomination_id>/delete", views.nomination_delete),
    path("votes/create", views.vote_create),
]
