from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.contrib import admin

def root_view(request):
    """Root path for health checks (GET / or HEAD /) - avoids 404."""
    return JsonResponse({"ok": True, "service": "recognition-api", "api": "/api/"})

def admin_redirect_info(request):
    return HttpResponse(
        "<h2>Admin is on the frontend</h2>"
        "<p>This is the API server. Open the <strong>Next.js frontend</strong> (e.g. <a href='http://localhost:3000'>http://localhost:3000</a>), "
        "then go to <a href='http://localhost:3000/admin'>/admin</a> to log in and manage sessions.</p>"
        "<p><strong>Participant emails (reusable list):</strong> <a href='/django-admin/recognition/recognitionemail/'>Django Admin → Participant emails</a></p>",
        content_type="text/html",
    )

urlpatterns = [
    path("", root_view),
    path("api/", include("recognition.urls")),
    path("admin/", admin_redirect_info),
    path("django-admin/", admin.site.urls),
]
