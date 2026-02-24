from django.contrib import admin
from .models import MeetingSession, Nomination, Vote


@admin.register(MeetingSession)
class MeetingSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "phase", "updated_at"]
    list_filter = ["phase"]
    list_per_page = 20


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ["nominee_name", "nominator_name", "session", "created_at"]
    list_filter = ["session"]
    list_per_page = 20


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ["voter_name", "session", "created_at"]
    list_filter = ["session"]
    list_per_page = 20
