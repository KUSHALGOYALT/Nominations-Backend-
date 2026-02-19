from django.contrib import admin
from .models import MeetingSession, Nomination, Vote


@admin.register(MeetingSession)
class MeetingSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "meeting_date", "phase", "winner_name", "created_at"]
    list_filter = ["phase"]
    search_fields = ["title", "winner_name"]


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ["session", "nominator_name", "nominee_name", "created_at"]
    list_filter = ["session"]
    search_fields = ["nominator_name", "nominee_name", "reason"]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ["session", "voter_name", "created_at"]
    list_filter = ["session"]
    search_fields = ["voter_name"]
