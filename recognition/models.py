from django.db import models


class MeetingSession(models.Model):
    """One meeting round; data cleared when closed."""
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.phase})"


class Nomination(models.Model):
    """Up to 3 nominations per person per session; deleted when session closes."""
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="nominations")
    nominator_name = models.CharField(max_length=255)
    nominee_name = models.CharField(max_length=255)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nominee_name}"


class Vote(models.Model):
    """One vote per session per person; deleted when session closes."""
    session = models.ForeignKey(MeetingSession, on_delete=models.CASCADE, related_name="votes")
    voter_name = models.CharField(max_length=255)
    nominations = models.ManyToManyField(Nomination, blank=True)  # empty = None of the above
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.voter_name}"
