"""
API tests for recognition app.
Run: python manage.py test recognition

Identity and single-use (no double vote / double nomination):
- We do not use email. Participants identify by a name they enter when joining.
- Per session: one nomination per nominator_name (UniqueConstraint + view check).
- Per session: one vote per voter_name (view check before creating vote).
- So the same person scanning the same session from a different QR/device and entering
  the same name cannot vote or nominate twice; the backend returns 400.
- The same name in a different session is allowed (identity is per session).
- Admin: single shared password (no email); any device with the password can admin.
"""
import json
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from .models import MeetingSession, Nomination, Vote


@override_settings(ADMIN_PASSWORD="test-admin-secret")
class SessionAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.auth = {"Authorization": "Bearer test-admin-secret"}

    def test_session_get_returns_none_when_no_sessions(self):
        r = self.client.get("/api/session")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsNone(data.get("session"))

    def test_session_get_returns_most_recently_updated_session(self):
        """Active session should be the one most recently updated, not most recently created."""
        older = MeetingSession.objects.create(
            title="Older Session",
            meeting_date=timezone.now().date(),
            phase="setup",
        )
        newer = MeetingSession.objects.create(
            title="Newer Session",
            meeting_date=timezone.now().date(),
            phase="setup",
        )
        # Initially "newer" is last updated (created most recently with default updated_at)
        r = self.client.get("/api/session")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["session"]["title"], "Newer Session")

        # Advance the OLDER session to nomination (updates its updated_at)
        r = self.client.patch(
            "/api/session/patch",
            data=json.dumps({"session_id": str(older.id), "phase": "nomination"}),
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": "Bearer test-admin-secret"},
        )
        self.assertEqual(r.status_code, 200)

        # Now GET should return the OLDER session (most recently updated)
        r = self.client.get("/api/session")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsNotNone(data["session"])
        self.assertEqual(data["session"]["title"], "Older Session")
        self.assertEqual(data["session"]["phase"], "nomination")

    def test_session_get_returns_phase_lowercase(self):
        s = MeetingSession.objects.create(
            title="Test",
            meeting_date=timezone.now().date(),
            phase="nomination",
        )
        r = self.client.get("/api/session")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["session"]["phase"], "nomination")

    def test_session_create_requires_admin(self):
        r = self.client.post(
            "/api/session/create",
            data=json.dumps({"title": "Test", "meeting_date": "2026-02-19"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_session_create_success(self):
        r = self.client.post(
            "/api/session/create",
            data=json.dumps({"title": "Fortnightly Review", "meeting_date": "2026-02-19"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-admin-secret",
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["session"]["title"], "Fortnightly Review")
        self.assertEqual(data["session"]["phase"], "setup")

    def test_session_patch_setup_to_nomination(self):
        s = MeetingSession.objects.create(
            title="Test",
            meeting_date=timezone.now().date(),
            phase="setup",
        )
        r = self.client.patch(
            "/api/session/patch",
            data=json.dumps({"session_id": str(s.id), "phase": "nomination"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-admin-secret",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["session"]["phase"], "nomination")
        s.refresh_from_db()
        self.assertEqual(s.phase, "nomination")

    def test_session_patch_nomination_to_voting(self):
        s = MeetingSession.objects.create(
            title="Test",
            meeting_date=timezone.now().date(),
            phase="nomination",
        )
        r = self.client.patch(
            "/api/session/patch",
            data=json.dumps({"session_id": str(s.id), "phase": "voting"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-admin-secret",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["session"]["phase"], "voting")

    def test_session_patch_invalid_transition_rejected(self):
        s = MeetingSession.objects.create(
            title="Test",
            meeting_date=timezone.now().date(),
            phase="setup",
        )
        r = self.client.patch(
            "/api/session/patch",
            data=json.dumps({"session_id": str(s.id), "phase": "voting"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-admin-secret",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.json())


@override_settings(ADMIN_PASSWORD="test-admin-secret")
class NominationAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.session = MeetingSession.objects.create(
            title="Test Session",
            meeting_date=timezone.now().date(),
            phase="nomination",
        )

    def test_nomination_create_success(self):
        r = self.client.post(
            "/api/nominations/create",
            data=json.dumps({
                "nominator_name": "Alice",
                "nominee_name": "Alice",
                "reason": "Did great work this sprint.",
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Nomination.objects.filter(session=self.session).count(), 1)

    def test_nomination_create_rejected_when_phase_not_nomination(self):
        self.session.phase = "setup"
        self.session.save()
        r = self.client.post(
            "/api/nominations/create",
            data=json.dumps({
                "nominator_name": "Alice",
                "nominee_name": "Alice",
                "reason": "Pitch.",
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_nomination_max_3_per_person(self):
        """Same person can nominate up to 3; 4th is rejected."""
        for i in range(3):
            Nomination.objects.create(
                session=self.session,
                nominator_name="Alice",
                nominee_name=f"Nominee{i}",
                reason=f"Pitch {i}.",
            )
        r = self.client.post(
            "/api/nominations/create",
            data=json.dumps({
                "nominator_name": "Alice",
                "nominee_name": "Fourth",
                "reason": "Fourth pitch.",
                "session_id": self.session.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("at most 3", (r.json().get("error") or "").lower())

    def test_nominations_list_returns_for_active_session(self):
        Nomination.objects.create(
            session=self.session,
            nominator_name="Alice",
            nominee_name="Alice",
            reason="Pitch.",
        )
        r = self.client.get("/api/nominations")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["nominations"]), 1)
        self.assertEqual(data["nominations"][0]["nominee_name"], "Alice")


@override_settings(ADMIN_PASSWORD="test-admin-secret")
class VoteAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.session = MeetingSession.objects.create(
            title="Vote Session",
            meeting_date=timezone.now().date(),
            phase="voting",
        )
        self.nom = Nomination.objects.create(
            session=self.session,
            nominator_name="Alice",
            nominee_name="Alice",
            reason="My pitch.",
        )

    def test_vote_create_success(self):
        r = self.client.post(
            "/api/votes/create",
            data=json.dumps({
                "voter_name": "Bob",
                "nomination_ids": [self.nom.id],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Vote.objects.filter(session=self.session).count(), 1)

    def test_vote_create_none_of_above(self):
        r = self.client.post(
            "/api/votes/create",
            data=json.dumps({
                "voter_name": "Bob",
                "nomination_ids": [],
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)

    def test_vote_rejected_when_phase_not_voting(self):
        self.session.phase = "nomination"
        self.session.save()
        r = self.client.post(
            "/api/votes/create",
            data=json.dumps({"voter_name": "Bob", "nomination_ids": [self.nom.id]}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_vote_duplicate_rejected(self):
        """Same person (voter_name) cannot vote twice in the same session (e.g. scanning same session from another device/QR)."""
        Vote.objects.create(session=self.session, voter_name="Bob")
        r = self.client.post(
            "/api/votes/create",
            data=json.dumps({"voter_name": "Bob", "nomination_ids": [self.nom.id], "session_id": self.session.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("already voted", (r.json().get("error") or "").lower())

    def test_same_name_can_vote_in_different_sessions(self):
        """Same name in a different session is allowed (identity is per session, not global)."""
        Vote.objects.create(session=self.session, voter_name="Bob")
        other_session = MeetingSession.objects.create(
            title="Other",
            meeting_date=timezone.now().date(),
            phase="voting",
        )
        other_nom = Nomination.objects.create(
            session=other_session,
            nominator_name="Alice",
            nominee_name="Alice",
            reason="Pitch.",
        )
        r = self.client.post(
            "/api/votes/create",
            data=json.dumps({"voter_name": "Bob", "nomination_ids": [other_nom.id], "session_id": other_session.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Vote.objects.filter(session=other_session, voter_name="Bob").count(), 1)


@override_settings(ADMIN_PASSWORD="test-admin-secret")
class AdminCheckTests(TestCase):
    def test_admin_check_401_without_header(self):
        r = self.client.get("/api/auth/check")
        self.assertEqual(r.status_code, 401)

    def test_admin_check_401_wrong_password(self):
        r = self.client.get("/api/auth/check", HTTP_AUTHORIZATION="Bearer wrong")
        self.assertEqual(r.status_code, 401)

    def test_admin_check_200_correct_password(self):
        r = self.client.get("/api/auth/check", HTTP_AUTHORIZATION="Bearer test-admin-secret")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("ok"), True)
