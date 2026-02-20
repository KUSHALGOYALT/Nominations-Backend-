import uuid
from django.db import models


class MeetingSession(models.Model):
    PHASE_CHOICES = [
        ("setup", "Setup"),
        ("nomination", "Nomination"),
        ("voting", "Voting"),
        ("results", "Results"),
        ("closed", "Closed"),
    ]
    title = models.CharField(max_length=255, default="Fortnightly Goal Review")
    meeting_date = models.DateField(null=True, blank=True)
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default="setup")
    winner_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.phase})"


class Nomination(models.Model):
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="nominations")
    nominator_name = models.CharField(max_length=255, default="Legacy User")
    nominee_name = models.CharField(max_length=255)  # Free text name
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "nominator_name"], name="one_nomination_per_person_per_session"),
        ]

    def __str__(self):
        return f"{self.nominator_name} nominated {self.nominee_name}"


class Vote(models.Model):
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="votes")
    voter_name = models.CharField(max_length=255, default="Legacy User")
    # A vote can be for specific nominations OR "None of the Above" (empty list handled in view logic)
    nominations = models.ManyToManyField(Nomination, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Removed to allow multiple votes (max 3)
        pass

    def __str__(self):
        return f"Vote by {self.voter_name}"
