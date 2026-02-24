from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.contrib import admin
from django.conf import settings

def root_view(request):
    return JsonResponse({"ok": True, "service": "recognition-api", "api": "/api/"})

def admin_redirect_info(request):
    """Point to frontend admin; API server has no admin UI."""
    base = getattr(settings, "APP_URL", "http://localhost:3000").rstrip("/")
    return HttpResponse(
        f"<p>API server. Frontend: <a href='{base}'>{base}</a> → <a href='{base}/admin'>/admin</a></p>",
        content_type="text/html",
    )

urlpatterns = [
    path("", root_view),
    path("api/", include("recognition.urls")),
    path("admin/", admin_redirect_info),
    path("django-admin/", admin.site.urls),
]
