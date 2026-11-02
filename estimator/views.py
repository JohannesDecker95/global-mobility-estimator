"""Serves the built front end (frontend/dist/index.html) at the site root.

The page loads its script and styles from /static/, which Django's staticfiles serves
while DEBUG is on (the default for local use). Rebuild with `npm run build` in frontend/.
"""
from django.conf import settings
from django.http import HttpResponse


def index(request):
    page = settings.FRONTEND_DIST / "index.html"
    if not page.exists():
        return HttpResponse(
            "The front end is not built. Run `npm install` and `npm run build` in frontend/, "
            "or use the API at /api/.", status=503, content_type="text/plain; charset=utf-8")
    return HttpResponse(page.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")
