import uuid
from django.db import models


class Participant(models.Model):
    """Reusable list of participant emails (managed in Django admin). Used for all sessions."""
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]
        verbose_name = "Participant"
        verbose_name_plural = "Participants"

    def __str__(self):
        return f"{self.email} ({self.token})"


class MeetingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Fortnightly Goal Review")
    meeting_date = models.DateField()
    phase = models.CharField(
        max_length=20,
        choices=[
            ("setup", "setup"),
            ("nomination", "nomination"),
            ("voting", "voting"),
            ("results", "results"),
            ("closed", "closed"),
        ],
        default="setup",
    )
    recognition_period_start = models.DateField(null=True, blank=True)
    recognition_period_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.meeting_date})"


class Nomination(models.Model):
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="nominations")
    nominator = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="nominations_made")
    nominee_name = models.CharField(max_length=255, default="Self")
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["session", "nominator"]  # One nomination per person per session (they pitch themselves)

    def __str__(self):
        return f"{self.nominator} nominated {self.nominee_name} ({self.session})"


class Vote(models.Model):
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="votes_cast")
    nomination = models.ForeignKey(Nomination, on_delete=models.CASCADE, related_name="votes", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together = ["session", "voter"]  # Removed to allow multiple votes (max 3)
        pass

    def __str__(self):
        return f"{self.voter} voted for {self.nomination}"
