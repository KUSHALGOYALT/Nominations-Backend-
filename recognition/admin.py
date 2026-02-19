from django.contrib import admin
from .models import Participant, MeetingSession, Nomination, Vote


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ["email", "token", "created_at"]
    search_fields = ["email"]
    ordering = ["email"]


@admin.register(MeetingSession)
class MeetingSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "meeting_date", "phase", "created_at"]
    list_filter = ["phase"]
    search_fields = ["title"]


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ["session", "nominator", "nominee_name", "created_at"]
    list_filter = ["session"]
    search_fields = ["nominator__email", "nominee_name"]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ["session", "voter", "nomination", "created_at"]
    list_filter = ["session"]
