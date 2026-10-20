import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from events.models import Event

from . import paystack
from .forms import CheckoutForm
from .models import Order
from .services import PaymentError, mark_failed, verify_and_fulfill

logger = logging.getLogger(__name__)


def _callback_url(request):
    configured = settings.PAYSTACK_CALLBACK_URL.strip()
    if configured:
        return configured
    return request.build_absolute_uri(reverse("orders:callback"))


class CheckoutView(LoginRequiredMixin, View):
    template_name = "orders/checkout.html"

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(
            Event, slug=kwargs["slug"], is_active=True, is_ticketed=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.event.is_on_sale:
            messages.error(request, "Tickets for this event are no longer available.")
            return redirect(self.event)
        initial = {
            "full_name": request.user.get_full_name() or request.user.get_username(),
            "email": request.user.email,
            "quantity": 1,
        }
        return render(
            request,
            self.template_name,
            {"event": self.event, "form": CheckoutForm(initial=initial)},
        )

    def post(self, request, *args, **kwargs):
        if not paystack.is_configured():
            messages.error(
                request,
                "Ticket payments aren't available right now. Please try again later.",
            )
            return redirect(self.event)

        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"event": self.event, "form": form},
                status=400,
            )

        if not self.event.is_on_sale:
            form.add_error(None, "Tickets for this event are no longer available.")
            return render(
                request,
                self.template_name,
                {"event": self.event, "form": form},
                status=409,
            )

        quantity = form.cleaned_data["quantity"]
        remaining = self.event.tickets_remaining
        if remaining is not None and quantity > remaining:
            form.add_error(
                "quantity",
                f"Only {remaining} ticket{'s' if remaining != 1 else ''} left.",
            )
            return render(
                request,
                self.template_name,
                {"event": self.event, "form": form},
                status=409,
            )

        order = Order.objects.create(
            user=request.user,
            event=self.event,
            full_name=form.cleaned_data["full_name"],
            email=form.cleaned_data["email"],
            quantity=quantity,
            unit_price_kobo=self.event.price_kobo,
            total_kobo=self.event.price_kobo * quantity,
            currency=settings.PAYSTACK_CURRENCY,
        )

        try:
            data = paystack.initialize_transaction(
                email=order.email,
                amount_kobo=order.total_kobo,
                reference=order.reference,
                callback_url=_callback_url(request),
                metadata={
                    "order_id": order.pk,
                    "event": self.event.slug,
                    "buyer_name": order.full_name,
                },
            )
        except paystack.PaystackError as exc:
            mark_failed(order, str(exc))
            logger.warning("Paystack init failed for %s: %s", order.reference, exc)
            messages.error(request, str(exc))
            return redirect("orders:checkout", slug=self.event.slug)

        order.gateway_reference = data.get("reference") or order.reference
        order.save(update_fields=["gateway_reference", "updated_at"])

        authorization_url = data["authorization_url"]
        if not authorization_url.startswith("https://"):
            logger.error("Refusing non-HTTPS Paystack URL for %s", order.reference)
            mark_failed(order, "Invalid checkout URL")
            messages.error(request, "We couldn't start a secure checkout. Please try again.")
            return redirect("orders:checkout", slug=self.event.slug)
        return redirect(authorization_url)


class PaystackCallbackView(LoginRequiredMixin, View):
    """Buyer returns here from Paystack; confirm server-side before trusting it."""

    def get(self, request):
        reference = (request.GET.get("reference") or "").strip()
        if not reference:
            messages.error(request, "We didn't receive a payment reference.")
            return redirect("orders:account")

        order = Order.objects.filter(reference=reference, user=request.user).first()
        if order is None:
            messages.error(request, "We couldn't find that order on your account.")
            return redirect("orders:account")

        try:
            order, fulfilled_now = verify_and_fulfill(order)
        except paystack.PaystackError as exc:
            logger.warning("Verification failed for %s: %s", reference, exc)
            messages.error(
                request,
                "We couldn't confirm your payment yet. Your tickets will be issued "
                "automatically once it clears.",
            )
        except PaymentError as exc:
            logger.warning("Rejected payment for %s: %s", reference, exc)
            messages.error(request, str(exc))
        else:
            if order.is_paid:
                if fulfilled_now:
                    messages.success(
                        request,
                        f"Payment confirmed! Your {order.quantity} ticket"
                        f"{'s are' if order.quantity != 1 else ' is'} on the way to {order.email}.",
                    )
                else:
                    messages.success(request, "This order is already confirmed.")
            else:
                messages.error(request, "This payment hasn't completed yet.")

        return redirect("orders:detail", token=order.access_token)


class OrderDetailView(LoginRequiredMixin, View):
    template_name = "orders/detail.html"

    def get(self, request, token):
        order = get_object_or_404(
            Order.objects.select_related("event").prefetch_related("tickets"),
            access_token=token,
            user=request.user,
        )
        return render(request, self.template_name, {"order": order})


class VerifyPaymentView(LoginRequiredMixin, View):
    def post(self, request, token):
        order = get_object_or_404(
            Order, access_token=token, user=request.user
        )
        if order.status == Order.Status.PAID:
            messages.success(request, "This order is already confirmed.")
            return redirect("orders:detail", token=order.access_token)

        try:
            order, fulfilled_now = verify_and_fulfill(order)
        except (paystack.PaystackError, PaymentError) as exc:
            messages.error(
                request,
                str(exc)
                if isinstance(exc, PaymentError)
                else "We couldn't reach Paystack. Please try again shortly.",
            )
        else:
            if fulfilled_now:
                messages.success(
                    request, "Payment confirmed — your tickets have been issued."
                )
            else:
                messages.success(request, "This order is already confirmed.")
        return redirect("orders:detail", token=order.access_token)


class AccountView(LoginRequiredMixin, View):
    template_name = "orders/account.html"

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .select_related("event")
            .prefetch_related("tickets")
        )
        return render(request, self.template_name, {"orders": orders})


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Signed, server-to-server payment notifications from Paystack."""
    signature = request.headers.get("x-paystack-signature", "")
    if not paystack.is_valid_webhook_signature(request.body, signature):
        logger.warning("Rejected Paystack webhook with bad signature")
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    if payload.get("event") != "charge.success":
        return JsonResponse({"status": "ignored"})

    data = payload.get("data") or {}
    reference = (data.get("reference") or "").strip()
    order = Order.objects.filter(reference=reference).first()
    if order is None:
        logger.warning("Webhook for unknown order reference %r", reference)
        return JsonResponse({"status": "ignored"})

    try:
        verify_and_fulfill(order, transaction_data=data)
    except PaymentError as exc:
        logger.warning("Webhook payment rejected for %s: %s", reference, exc)
        return JsonResponse({"status": "rejected"}, status=200)
    except Exception:
        logger.exception("Webhook fulfilment failed for %s", reference)
        return HttpResponse(status=500)

    return JsonResponse({"status": "ok"})
