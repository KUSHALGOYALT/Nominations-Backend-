from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.contrib import admin
from django.conf import settings

def root_view(request):
    """Root path for health checks (GET / or HEAD /) - avoids 404."""
    return JsonResponse({"ok": True, "service": "recognition-api", "api": "/api/"})

def admin_redirect_info(request):
    frontend_url = getattr(settings, "APP_URL", "http://localhost:3000").rstrip("/")
    admin_url = f"{frontend_url}/admin"
    return HttpResponse(
        f"<h2>Admin is on the frontend</h2>"
        f"<p>This is the API server. Open the <strong>Next.js frontend</strong>: "
        f"<a href='{frontend_url}'>{frontend_url}</a>, "
        f"then go to <a href='{admin_url}'>/admin</a> to log in and manage sessions.</p>"
        f"<p><strong>Participant emails (reusable list):</strong> <a href='/django-admin/recognition/recognitionemail/'>Django Admin → Participant emails</a></p>",
        content_type="text/html",
    )

urlpatterns = [
    path("", root_view),
    path("api/", include("recognition.urls")),
    path("admin/", admin_redirect_info),
    path("django-admin/", admin.site.urls),
]
