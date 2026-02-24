import json
from django.db.models import Count
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import MeetingSession, Nomination, Vote


def admin_required(f):
    def wrapped(request, *args, **kwargs):
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer ") or auth[7:] != settings.ADMIN_PASSWORD:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return f(request, *args, **kwargs)
    return wrapped


def session_to_dict(s):
    return {
        "id": str(s.id),
        "title": s.title,
        "meeting_date": str(s.meeting_date) if s.meeting_date else None,
        "phase": (s.phase or "setup").lower(),
        "created_at": s.created_at.isoformat(),
    }


def _get_results_for_session(session):
    """Vote counts, winners, none_of_above for results/closed phase."""
    nominations = session.nominations.all()
    name_to_count = {}
    for n in nominations:
        c = Vote.objects.filter(session=session, nominations=n).count()
        name_to_count[n.nominee_name] = name_to_count.get(n.nominee_name, 0) + c
    vote_counts = sorted([{"name": k, "count": v} for k, v in name_to_count.items()], key=lambda x: -x["count"])
    max_count = vote_counts[0]["count"] if vote_counts else 0
    winners = [x["name"] for x in vote_counts if x["count"] == max_count and max_count > 0]
    none_of_above_count = Vote.objects.filter(session=session).annotate(nc=Count("nominations")).filter(nc=0).count()
    return {"vote_counts": vote_counts, "winners": winners, "none_of_above_count": none_of_above_count}


def _resolve_session(request, session_id_from_body=None):
    """Session from GET session_id, body session_id, or most recent."""
    sid = request.GET.get("session_id") or session_id_from_body
    if sid:
        try:
            return MeetingSession.objects.get(id=sid)
        except (MeetingSession.DoesNotExist, ValueError):
            return None
    return MeetingSession.objects.order_by("-updated_at").first()


VALID_TRANSITIONS = {
    "setup": ["nomination"],
    "nomination": ["voting", "setup"],
    "voting": ["results", "nomination"],
    "results": ["closed", "voting"],
    "closed": [],
}


@require_http_methods(["GET"])
@admin_required
def admin_check(request):
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def session_get(request):
    """GET session; returns results (vote_counts, winners, none_of_above) only when phase is results/closed."""
    sid = request.GET.get("session_id")
    if sid:
        try:
            session = MeetingSession.objects.get(id=sid)
        except (MeetingSession.DoesNotExist, ValueError):
            return JsonResponse({"session": None, "error": "Session not found"})
    else:
        session = MeetingSession.objects.exclude(phase="closed").order_by("-updated_at").first()

    payload = {"session": session_to_dict(session) if session else None}
    if session:
        phase = (session.phase or "").lower()
        if phase in ("results", "closed"):
            payload.update(_get_results_for_session(session))
        else:
            payload["vote_counts"], payload["winners"], payload["none_of_above_count"] = [], [], 0
    return JsonResponse(payload)


@require_http_methods(["GET"])
def qr_join(request):
    """Redirect to frontend /vote with session_id."""
    base = getattr(settings, "APP_URL", "http://localhost:3000").rstrip("/")
    sid = request.GET.get("session_id")
    if not sid:
        return redirect(f"{base}/vote?error=missing_session")
    try:
        session = MeetingSession.objects.get(id=sid)
    except (MeetingSession.DoesNotExist, ValueError):
        return redirect(f"{base}/vote?error=invalid_session")
    if (session.phase or "").lower() == "closed":
        return redirect(f"{base}/vote?session_id={sid}&error=session_ended")
    return redirect(f"{base}/vote?session_id={sid}")


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
def session_create(request):
    data = json.loads(request.body)
    meeting_date = data.get("meeting_date") or timezone.now().date().isoformat()
    session = MeetingSession.objects.create(
        title=data.get("title") or "Fortnightly Goal Review",
        meeting_date=meeting_date,
        phase="setup",
    )
    return JsonResponse({"session": session_to_dict(session)}, status=201)


@csrf_exempt
@admin_required
@require_http_methods(["PATCH"])
def session_patch(request):
    data = json.loads(request.body)
    sid, phase = data.get("session_id"), data.get("phase")
    if not sid or not phase:
        return JsonResponse({"error": "session_id and phase required"}, status=400)
    session = get_object_or_404(MeetingSession, id=sid)
    if phase not in VALID_TRANSITIONS.get(session.phase, []):
        return JsonResponse({"error": f"Cannot transition from '{session.phase}' to '{phase}'"}, status=400)
    session.phase = phase
    session.save()
    if (phase or "").lower() == "closed":
        Vote.objects.filter(session=session).delete()
        Nomination.objects.filter(session=session).delete()
    return JsonResponse({"session": session_to_dict(session)})


@require_http_methods(["GET"])
def nominations_list(request):
    session = _resolve_session(request)
    if not session:
        return JsonResponse({"nominations": []})
    qs = session.nominations.all().order_by(Lower("nominee_name"))
    data = [{"id": n.id, "nominator_name": n.nominator_name, "nominee_name": n.nominee_name, "reason": n.reason} for n in qs]
    return JsonResponse({"nominations": data})


@csrf_exempt
@require_http_methods(["POST"])
def nomination_create(request):
    data = json.loads(request.body)
    nominator_name, nominee_name, reason = data.get("nominator_name"), data.get("nominee_name"), data.get("reason")
    if not all([nominator_name, nominee_name, reason]):
        return JsonResponse({"error": "Missing fields"}, status=400)
    session = _resolve_session(request, data.get("session_id"))
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)
    if session.phase != "nomination":
        return JsonResponse({"error": "Session not in nomination phase"}, status=400)
    count = Nomination.objects.filter(session=session, nominator_name=nominator_name).count()
    if count >= 3:
        return JsonResponse({"error": "You can nominate at most 3 people per session."}, status=400)
    Nomination.objects.create(session=session, nominator_name=nominator_name, nominee_name=nominee_name, reason=reason)
    return JsonResponse({"ok": True}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def vote_create(request):
    data = json.loads(request.body)
    voter_name, nomination_ids = data.get("voter_name"), data.get("nomination_ids", [])
    if not voter_name:
        return JsonResponse({"error": "Voter name required"}, status=400)
    session = _resolve_session(request, data.get("session_id"))
    if not session:
        return JsonResponse({"error": "Session not found"}, status=404)
    if session.phase != "voting":
        return JsonResponse({"error": "Session not in voting phase"}, status=400)
    if Vote.objects.filter(session=session, voter_name=voter_name).exists():
        return JsonResponse({"error": "You have already voted"}, status=400)
    if len(nomination_ids) > 3:
        return JsonResponse({"error": "You can select up to 3 candidates."}, status=400)
    vote = Vote.objects.create(session=session, voter_name=voter_name)
    if nomination_ids:
        vote.nominations.set(Nomination.objects.filter(session=session, id__in=nomination_ids))
    return JsonResponse({"ok": True}, status=201)


@csrf_exempt
@admin_required
@require_http_methods(["DELETE"])
def nomination_delete(request, nomination_id):
    nomination = get_object_or_404(Nomination, id=nomination_id)
    nomination.delete()
    return JsonResponse({"ok": True})
