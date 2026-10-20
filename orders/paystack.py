"""Small Paystack API client (hosted checkout flow)."""

import hashlib
import hmac
import logging
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackError(Exception):
    """Raised when Paystack cannot complete a request."""


def is_configured():
    return bool(settings.PAYSTACK_SECRET_KEY)


def _secret_key():
    key = settings.PAYSTACK_SECRET_KEY
    if not key:
        raise PaystackError("Ticket payments are not configured yet.")
    return key


def _request(method, path, *, json=None):
    url = f"{settings.PAYSTACK_BASE_URL.rstrip('/')}{path}"
    try:
        response = requests.request(
            method,
            url,
            json=json,
            headers={
                "Authorization": f"Bearer {_secret_key()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.exception("Paystack request failed: %s %s", method, path)
        raise PaystackError(
            "We couldn't reach Paystack. Please try again in a moment."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.error("Paystack returned a non-JSON response (%s)", response.status_code)
        raise PaystackError("Paystack returned an unexpected response.") from exc

    if not payload.get("status"):
        message = payload.get("message") or "Paystack could not process this request."
        logger.warning("Paystack rejected %s %s: %s", method, path, message)
        raise PaystackError(message)

    return payload.get("data") or {}


def initialize_transaction(*, email, amount_kobo, reference, callback_url, metadata=None):
    """Create a hosted checkout and return its authorization URL."""
    data = _request(
        "POST",
        "/transaction/initialize",
        json={
            "email": email,
            "amount": amount_kobo,
            "currency": settings.PAYSTACK_CURRENCY,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata or {},
        },
    )
    if not data.get("authorization_url"):
        raise PaystackError("Paystack did not return a checkout URL.")
    return data


def verify_transaction(reference):
    """Fetch the authoritative transaction state for a reference."""
    return _request("GET", f"/transaction/verify/{quote(reference, safe='')}")


def is_valid_webhook_signature(payload, signature):
    """Check Paystack's HMAC SHA512 signature against the raw request body."""
    secret = settings.PAYSTACK_SECRET_KEY
    if not secret or not signature or payload is None:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
