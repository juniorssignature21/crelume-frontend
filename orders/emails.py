import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


def send_ticket_email(order):
    """Email every ticket for a paid order to the buyer."""
    tickets = list(order.tickets.order_by("sequence", "id"))
    if not tickets:
        logger.warning("No tickets to email for order %s", order.reference)
        return

    event = order.event
    context = {
        "order": order,
        "event": event,
        "tickets": tickets,
        "contact_email": settings.CONTACT_EMAIL,
        "site_url": settings.SITE_URL,
        "order_url": f"{settings.SITE_URL.rstrip('/')}{order.get_absolute_url()}",
    }
    subject = f"{settings.TICKET_EMAIL_SUBJECT} — {event.name}"
    text_body = render_to_string("emails/tickets.txt", context)
    html_body = render_to_string("emails/tickets.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
        reply_to=[settings.CONTACT_EMAIL],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def send_ticket_email_for_order(order_pk):
    """Send once per order, tracking delivery so retries don't spam buyers."""
    claimed = Order.objects.filter(
        pk=order_pk, status=Order.Status.PAID, email_sent_at__isnull=True
    ).update(email_sent_at=timezone.now())
    if not claimed:
        return

    order = Order.objects.select_related("event").filter(pk=order_pk).first()
    if order is None:
        return
    try:
        send_ticket_email(order)
    except Exception:
        logger.exception("Could not email tickets for order %s", order.reference)
        # Allow a later retry; the buyer still has the tickets on their order page.
        Order.objects.filter(pk=order_pk).update(email_sent_at=None)
