"""Payment verification, fulfilment and ticket issuance."""

import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import paystack
from .emails import send_ticket_email_for_order
from .models import Order, Ticket

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when a payment cannot be verified or trusted."""


def _sanitize_transaction(data):
    """Keep only the non-sensitive fields needed for support and auditing."""
    return {
        "status": data.get("status"),
        "reference": data.get("reference"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "channel": data.get("channel"),
        "gateway_response": data.get("gateway_response"),
        "paid_at": data.get("paid_at"),
    }


def _ensure_matches(order, data):
    if data.get("status") != "success":
        raise PaymentError("This payment was not successful.")
    if data.get("reference") != order.reference:
        raise PaymentError("This payment does not match the order.")
    try:
        amount = int(data.get("amount"))
    except (TypeError, ValueError) as exc:
        raise PaymentError("Paystack did not return a valid amount.") from exc
    if amount != order.total_kobo:
        logger.error(
            "Amount mismatch for %s: expected %s, got %s",
            order.reference,
            order.total_kobo,
            amount,
        )
        raise PaymentError("The amount paid does not match this order.")
    currency = str(data.get("currency") or "").upper()
    if currency != order.currency.upper():
        raise PaymentError("The payment currency does not match this order.")


def verify_and_fulfill(order, transaction_data=None):
    """Verify a transaction with Paystack and issue tickets exactly once.

    Returns ``(order, fulfilled_now)``. Safe to call from both the browser
    callback and the webhook; the order row is locked and the status check
    makes duplicate calls no-ops.
    """
    if transaction_data is None:
        transaction_data = paystack.verify_transaction(order.reference)

    _ensure_matches(order, transaction_data)

    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status == Order.Status.PAID:
            return locked, False

        now = timezone.now()
        locked.status = Order.Status.PAID
        locked.paid_at = now
        locked.gateway_reference = transaction_data.get("reference") or locked.reference
        locked.gateway_response = _sanitize_transaction(transaction_data)
        locked.save(
            update_fields=[
                "status",
                "paid_at",
                "gateway_reference",
                "gateway_response",
                "updated_at",
            ]
        )

        tickets = [
            Ticket(
                order=locked,
                event=locked.event,
                sequence=index,
                attendee_name=locked.full_name,
                attendee_email=locked.email,
            )
            for index in range(locked.quantity)
        ]
        try:
            with transaction.atomic():
                Ticket.objects.bulk_create(tickets)
        except IntegrityError:
            # Another request issued tickets for this order first; keep theirs.
            logger.warning("Ticket issuance raced for order %s", locked.reference)
            return locked, False

        order_pk = locked.pk
        transaction.on_commit(lambda: send_ticket_email_for_order(order_pk))

    return locked, True


def mark_failed(order, reason=""):
    Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(
        status=Order.Status.FAILED,
        gateway_response={"message": reason} if reason else {},
        updated_at=timezone.now(),
    )
