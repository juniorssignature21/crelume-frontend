import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from events.models import Event

from .forms import ContactForm

logger = logging.getLogger(__name__)


def _home_context(contact_form=None):
    events = Event.objects.filter(is_active=True).order_by("starts_at", "id")
    upcoming_events = sorted(
        (event for event in events if event.starts_at),
        key=lambda event: (not event.is_featured, event.starts_at),
    )
    return {
        "events": events,
        "upcoming_events": upcoming_events,
        "featured_event": events.filter(is_featured=True).first(),
        "online_event": events.filter(is_online=True).first(),
        "contact_form": contact_form or ContactForm(),
    }


def home(request):
    return render(request, "core/home.html", _home_context())


@require_GET
def healthz(request):
    """Liveness/readiness probe used by the hosting platform."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # pragma: no cover - only hit when the database is down
        logger.exception("Health check failed")
        return JsonResponse(
            {"status": "error", "database": "unavailable"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "ok"})


@require_POST
def contact(request):
    form = ContactForm(request.POST)
    if not form.is_valid():
        return render(request, "core/home.html", _home_context(form), status=400)

    message = form.save(commit=False)
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    message.ip_address = (
        forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    )
    message.save()

    body = render_to_string(
        "emails/contact.txt",
        {
            "name": message.name,
            "email": message.email,
            "about": message.about,
            "message": message.message,
        },
    )
    try:
        send_mail(
            subject=f"Crelume contact: {message.about}",
            message=body,
            from_email=None,
            recipient_list=[settings.CONTACT_EMAIL],
        )
    except Exception:  # pragma: no cover - delivery failures should not lose messages
        logger.exception("Could not send contact notification")

    first_name = message.name.split()[0] if message.name.split() else "friend"
    messages.success(
        request, f"Thanks, {first_name} — we'll get back to you soon."
    )
    return redirect("/#contact")


def not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return HttpResponse(
        render_to_string("500.html", request=request), status=500
    )
