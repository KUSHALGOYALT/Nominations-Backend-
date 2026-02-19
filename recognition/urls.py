from django.urls import path
from . import views

urlpatterns = [
    path("auth/check", views.admin_check),
    path("session", views.session_get),
    path("session/create", views.session_create),
    path("session/patch", views.session_patch),
    path("participants", views.participants_list),
    path("participants/create", views.participants_create),
    path("participants/check", views.participant_by_token),
    path("participants/send-email", views.participants_send_email),
    
    path("nominations", views.nominations_list),
    path("nominations/create", views.nomination_create),
    path("votes/create", views.vote_create),
]
