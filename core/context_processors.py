from django.conf import settings


def site_globals(request):
    """Template-friendly flags for optional integrations."""
    return {
        "contact_email": settings.CONTACT_EMAIL,
        "google_auth_enabled": bool(
            settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET
        ),
        "github_auth_enabled": bool(
            settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET
        ),
        "paystack_enabled": bool(settings.PAYSTACK_SECRET_KEY),
        "max_ticket_quantity": settings.TICKET_MAX_QUANTITY,
    }
