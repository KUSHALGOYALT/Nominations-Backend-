import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import MeetingSession, Participant, Nomination, Vote


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
        "recognition_period_start": str(s.recognition_period_start) if s.recognition_period_start else None,
        "recognition_period_end": str(s.recognition_period_end) if s.recognition_period_end else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


# ----- Admin check (for login validation) -----
@require_http_methods(["GET"])
@admin_required
def admin_check(request):
    return JsonResponse({"ok": True})


# ----- Session -----
@require_http_methods(["GET"])
def session_get(request):
    session = MeetingSession.objects.exclude(phase="closed").order_by("-created_at").first()
    return JsonResponse({"session": session_to_dict(session) if session else None})


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
        recognition_period_start=data.get("recognition_period_start"),
        recognition_period_end=data.get("recognition_period_end"),
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


# ----- Participants -----
@require_http_methods(["GET"])
@admin_required
def participants_list(request):
    participants = Participant.objects.all().order_by("email")
    data = []
    for p in participants:
        data.append({
            "email": p.email,
            "token": str(p.token),
            "created_at": p.created_at
        })
    return JsonResponse({"participants": data})


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
def participants_create(request):
    data = json.loads(request.body)
    emails = data.get("emails", [])
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    
    created_count = 0
    duplicate_count = 0
    
    for email in emails:
        _, created = Participant.objects.get_or_create(email=email)
        if created:
            created_count += 1
        else:
            duplicate_count += 1
            
    return JsonResponse({
        "message": f"Added {created_count} participants. {duplicate_count} skipped.",
        "added": created_count,
        "skipped": duplicate_count
    })


@require_http_methods(["GET"])
def participant_by_token(request):
    token = request.GET.get("token")
    if not token:
        return JsonResponse({"error": "Token required"}, status=400)
    
    participant = get_object_or_404(Participant, token=token)
    
    # Get active session
    session = MeetingSession.objects.exclude(phase="closed").order_by("-created_at").first()
    
    has_nominated = False
    has_voted = False

    if session:
        has_nominated = Nomination.objects.filter(session=session, nominator=participant).exists()
        has_voted = Vote.objects.filter(session=session, voter=participant).exists()
    
    return JsonResponse({
        "participant": {"email": participant.email, "id": participant.id},
        "session": session_to_dict(session) if session else None,
        "has_nominated": has_nominated,
        "has_voted": has_voted
    })


@csrf_exempt
@admin_required
@require_http_methods(["POST"])
def participants_send_email(request):
    from django.core.mail import send_mail
    data = json.loads(request.body)
    emails = data.get("emails", [])
    
    participants = Participant.objects.filter(email__in=emails)
    sent_count = 0
    
    for p in participants:
        link = f"{settings.APP_URL}/vote?token={p.token}"
        try:
            send_mail(
                subject="Your Hexa Climate Voting Link",
                message=f"Hello,\n\nPlease use the following link to participate in the recognition session:\n\n{link}\n\nThank you,\nHexa Climate Team",
                from_email=None, # Uses DEFAULT_FROM_EMAIL
                recipient_list=[p.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send email to {p.email}: {e}")

    return JsonResponse({"sent": sent_count, "total": len(emails)})


# ----- Nominations & Votes -----

@require_http_methods(["GET"])
def nominations_list(request):
    """List all nominations for the active session (for voting)"""
    session = MeetingSession.objects.exclude(phase="closed").order_by("-created_at").first()
    if not session:
        return JsonResponse({"nominations": []})
        
    nominations = session.nominations.all()
    data = []
    for n in nominations:
        data.append({
            "id": n.id,
            "nominee_name": n.nominee_name,
            "reason": n.reason
        })
    return JsonResponse({"nominations": data})


@csrf_exempt
@require_http_methods(["POST"])
def nomination_create(request):
    data = json.loads(request.body)
    token = data.get("token")
    nominee_name = data.get("nominee_name")
    reason = data.get("reason")
    
    if not token or not nominee_name or not reason:
        return JsonResponse({"error": "Missing fields"}, status=400)
        
    nominator = get_object_or_404(Participant, token=token)
    session = MeetingSession.objects.exclude(phase="closed").order_by("-created_at").first()
    
    if not session or session.phase != "nomination":
        return JsonResponse({"error": "Session not in nomination phase"}, status=400)
        
    if Nomination.objects.filter(session=session, nominator=nominator).exists():
        return JsonResponse({"error": "You have already nominated"}, status=400)
        
    Nomination.objects.create(
        session=session,
        nominator=nominator,
        nominee_name=nominee_name,
        reason=reason
    )
    
    return JsonResponse({"ok": True}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def vote_create(request):
    data = json.loads(request.body)
    token = data.get("token")
    nomination_ids = data.get("nomination_ids", [])  # List of IDs or empty for "None"
    
    if not token:
        return JsonResponse({"error": "Token required"}, status=400)
    
    if len(nomination_ids) > 3:
        return JsonResponse({"error": "You can select up to 3 options only"}, status=400)
        
    voter = get_object_or_404(Participant, token=token)
    session = MeetingSession.objects.exclude(phase="closed").order_by("-created_at").first()
    
    if not session or session.phase != "voting":
        return JsonResponse({"error": "Session not in voting phase"}, status=400)
        
    if Vote.objects.filter(session=session, voter=voter).exists():
        return JsonResponse({"error": "You have already voted"}, status=400)
    
    if len(nomination_ids) == 0:
        # "None of the above" -> Create a Vote with null nomination to record participation
        Vote.objects.create(session=session, voter=voter, nomination=None)
    else:
        created_votes = []
        for limit_id in nomination_ids:
            nom = get_object_or_404(Nomination, id=limit_id)
            created_votes.append(Vote(session=session, voter=voter, nomination=nom))
        Vote.objects.bulk_create(created_votes)
    
    return JsonResponse({"ok": True}, status=201)
