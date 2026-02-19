import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import MeetingSession, Nomination, Vote


def admin_required(f):
    def wrapped(request, *args, **kwargs):
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        if auth[7:] != settings.ADMIN_PASSWORD:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return f(request, *args, **kwargs)
    return wrapped


def session_to_dict(s):
    return {
        "id": str(s.id),
        "title": s.title,
        "meeting_date": str(s.meeting_date),
        "phase": s.phase,
        "created_at": s.created_at.isoformat(),
    }


# ----- Admin check (for login validation) -----
@require_http_methods(["GET"])
@admin_required
def admin_check(request):
    return JsonResponse({"ok": True})


# ----- Session -----
@require_http_methods(["GET"])
def session_get(request):
    session = MeetingSession.objects.order_by("-created_at").first()
    return JsonResponse({"session": session_to_dict(session) if session else None})


@require_http_methods(["GET"])
def qr_scan(request):
    """Redirects QR scan to the frontend voting page"""
    # Use APP_URL from settings, or fall back to a default if not set
    frontend_url = getattr(settings, "APP_URL", "https://nominations-frontend.vercel.app")
    # Ensure no trailing slash for clean appending
    frontend_url = frontend_url.rstrip("/")
    from django.shortcuts import redirect
    return redirect(f"{frontend_url}/vote")


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
def session_create(request):
    from django.utils import timezone
    data = json.loads(request.body)
    from datetime import date
    meeting_date = data.get("meeting_date") or timezone.now().date().isoformat()
    session = MeetingSession.objects.create(
        title=data.get("title") or "Fortnightly Goal Review",
        meeting_date=meeting_date,
        phase="setup",
    )
    return JsonResponse({"session": session_to_dict(session)}, status=201)


VALID_TRANSITIONS = {
    "setup": ["nomination"],
    "nomination": ["voting"],
    "voting": ["results"],
    "results": ["closed"],
    "closed": [],
}


@csrf_exempt
@admin_required
@require_http_methods(["PATCH"])
def session_patch(request):
    data = json.loads(request.body)
    session_id = data.get("session_id")
    phase = data.get("phase")
    if not session_id or not phase:
        return JsonResponse({"error": "session_id and phase required"}, status=400)
    session = get_object_or_404(MeetingSession, id=session_id)
    current = session.phase
    if phase not in VALID_TRANSITIONS.get(current, []):
        return JsonResponse(
            {"error": f"Cannot transition from '{current}' to '{phase}'"},
            status=400,
        )
    session.phase = phase
    session.save()
    return JsonResponse({"session": session_to_dict(session)})


# ----- Nominations & Votes -----

@require_http_methods(["GET"])
def nominations_list(request):
    """List all nominations for the active session (for voting)"""
    session = MeetingSession.objects.order_by("-created_at").first()
    if not session:
        return JsonResponse({"nominations": []})
        
    nominations = session.nominations.all().order_by("-created_at")
    data = []
    for n in nominations:
        data.append({
            "id": n.id,
            "nominator_name": n.nominator_name,
            "nominee_name": n.nominee_name,
            "reason": n.reason
        })
    return JsonResponse({"nominations": data})


@csrf_exempt
@require_http_methods(["POST"])
def nomination_create(request):
    data = json.loads(request.body)
    nominator_name = data.get("nominator_name")
    nominee_name = data.get("nominee_name")
    reason = data.get("reason")
    
    if not all([nominator_name, nominee_name, reason]):
        return JsonResponse({"error": "Missing fields"}, status=400)
        
    session = MeetingSession.objects.order_by("-created_at").first()
    
    if not session or session.phase != "nomination":
        return JsonResponse({"error": "Session not in nomination phase"}, status=400)
        
    if Nomination.objects.filter(session=session, nominator_name=nominator_name).exists():
        return JsonResponse({"error": "You have already nominated"}, status=400)
        
    Nomination.objects.create(
        session=session,
        nominator_name=nominator_name,
        nominee_name=nominee_name,
        reason=reason
    )
    return JsonResponse({"ok": True}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def vote_create(request):
    data = json.loads(request.body)
    voter_name = data.get("voter_name")
    nomination_ids = data.get("nomination_ids", [])
    
    if not voter_name:
        return JsonResponse({"error": "Voter name required"}, status=400)
        
    session = MeetingSession.objects.order_by("-created_at").first()
    
    if not session or session.phase != "voting":
        return JsonResponse({"error": "Session not in voting phase"}, status=400)
        
    if Vote.objects.filter(session=session, voter_name=voter_name).exists():
        return JsonResponse({"error": "You have already voted"}, status=400)
    
    if len(nomination_ids) > 3:
         return JsonResponse({"error": "You can select up to 3 candidates."}, status=400)

    vote = Vote.objects.create(session=session, voter_name=voter_name)
    
    if nomination_ids:
        nominations = Nomination.objects.filter(session=session, id__in=nomination_ids)
        vote.nominations.set(nominations)
    
    return JsonResponse({"ok": True}, status=201)


@csrf_exempt
@admin_required
@require_http_methods(["DELETE"])
def nomination_delete(request, nomination_id):
    nomination = get_object_or_404(Nomination, id=nomination_id)
    nomination.delete()
    return JsonResponse({"ok": True})
