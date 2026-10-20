import hashlib
import hmac
import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from events.models import Event

from .models import Order, Ticket
from .services import PaymentError, verify_and_fulfill

PAYSTACK_SETTINGS = {
    "PAYSTACK_SECRET_KEY": "sk_test_crelume_tests",
    "PAYSTACK_CURRENCY": "NGN",
    "SITE_URL": "http://testserver",
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
}


def transaction_for(order, **overrides):
    data = {
        "status": "success",
        "reference": order.reference,
        "amount": order.total_kobo,
        "currency": order.currency,
        "channel": "card",
        "gateway_response": "Successful",
        "paid_at": "2026-10-18T12:00:00.000Z",
    }
    data.update(overrides)
    return data


@override_settings(**PAYSTACK_SETTINGS)
class CheckoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="Strong-pass-123!",
        )
        self.event = Event.objects.get(slug="creative-rebirth-live")
        self.checkout_url = reverse("orders:checkout", args=[self.event.slug])

    def test_checkout_requires_login(self):
        response = self.client.get(self.checkout_url)
        self.assertRedirects(
            response,
            f"{reverse('account_login')}?next={self.checkout_url}",
            fetch_redirect_response=False,
        )

        response = self.client.post(self.checkout_url, {"quantity": 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    @patch("orders.views.paystack.initialize_transaction")
    def test_checkout_creates_order_with_server_side_pricing(self, initialize, _captcha):
        self.client.force_login(self.user)
        self.event.price_kobo = 100_000
        self.event.save(update_fields=["price_kobo"])

        initialize.return_value = {
            "authorization_url": "https://checkout.paystack.com/abc123",
            "reference": "placeholder",
            "access_code": "abc123",
        }

        response = self.client.post(
            self.checkout_url,
            {
                "quantity": 3,
                "full_name": "Ada Buyer",
                "email": "ada@example.com",
                "unit_price_kobo": 1,
                "total_kobo": 1,
                "g-recaptcha-response": "test",
            },
        )

        self.assertRedirects(
            response,
            "https://checkout.paystack.com/abc123",
            fetch_redirect_response=False,
        )
        order = Order.objects.get()
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.quantity, 3)
        self.assertEqual(order.unit_price_kobo, 100_000)
        self.assertEqual(order.total_kobo, 300_000)
        self.assertEqual(order.status, Order.Status.PENDING)
        initialize.assert_called_once()
        _, kwargs = initialize.call_args
        self.assertEqual(kwargs["amount_kobo"], 300_000)
        self.assertEqual(kwargs["reference"], order.reference)
        self.assertEqual(kwargs["email"], "ada@example.com")

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    @patch("orders.views.paystack.initialize_transaction")
    def test_quantity_over_limit_is_rejected(self, initialize, _captcha):
        self.client.force_login(self.user)
        response = self.client.post(
            self.checkout_url,
            {
                "quantity": settings.TICKET_MAX_QUANTITY + 1,
                "full_name": "Ada Buyer",
                "email": "ada@example.com",
                "g-recaptcha-response": "test",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        initialize.assert_not_called()

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    @patch("orders.views.paystack.initialize_transaction")
    def test_cannot_buy_more_than_remaining(self, initialize, _captcha):
        self.client.force_login(self.user)
        self.event.capacity = 2
        self.event.save(update_fields=["capacity"])

        response = self.client.post(
            self.checkout_url,
            {
                "quantity": 3,
                "full_name": "Ada Buyer",
                "email": "ada@example.com",
                "g-recaptcha-response": "test",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Order.objects.count(), 0)
        initialize.assert_not_called()

    @patch("orders.views.paystack.initialize_transaction")
    def test_paystack_failure_marks_order_failed(self, initialize):
        from orders import paystack

        initialize.side_effect = paystack.PaystackError("Checkout unavailable")
        self.client.force_login(self.user)
        with patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None):
            response = self.client.post(
                self.checkout_url,
                {
                    "quantity": 1,
                    "full_name": "Ada Buyer",
                    "email": "ada@example.com",
                    "g-recaptcha-response": "test",
                },
            )
        self.assertRedirects(response, self.checkout_url)
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.FAILED)

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    @patch("orders.views.paystack.initialize_transaction")
    def test_non_https_checkout_url_is_refused(self, initialize, _captcha):
        initialize.return_value = {
            "authorization_url": "http://insecure.example.com/checkout",
            "reference": "placeholder",
        }
        self.client.force_login(self.user)
        response = self.client.post(
            self.checkout_url,
            {
                "quantity": 1,
                "full_name": "Ada Buyer",
                "email": "ada@example.com",
                "g-recaptcha-response": "test",
            },
        )
        self.assertRedirects(response, self.checkout_url)
        self.assertEqual(Order.objects.get().status, Order.Status.FAILED)


@override_settings(**PAYSTACK_SETTINGS)
class FulfilmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="Strong-pass-123!",
        )
        self.event = Event.objects.get(slug="creative-rebirth-live")
        self.order = Order.objects.create(
            user=self.user,
            event=self.event,
            full_name="Ada Buyer",
            email="ada@example.com",
            quantity=2,
            unit_price_kobo=100_000,
            total_kobo=200_000,
        )

    def test_success_issues_tickets_once_and_emails_them(self):
        with self.captureOnCommitCallbacks(execute=True):
            order, fulfilled_now = verify_and_fulfill(
                self.order, transaction_for(self.order)
            )

        self.assertTrue(fulfilled_now)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertIsNotNone(order.paid_at)
        self.assertIsNotNone(order.email_sent_at)
        self.assertEqual(order.gateway_response["status"], "success")
        self.assertNotIn("authorization", order.gateway_response)

        tickets = list(order.tickets.order_by("sequence"))
        self.assertEqual(len(tickets), 2)
        self.assertEqual([ticket.sequence for ticket in tickets], [0, 1])
        self.assertEqual(len({ticket.code for ticket in tickets}), 2)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["ada@example.com"])
        self.assertIn(self.event.name, email.subject)
        for ticket in tickets:
            self.assertIn(ticket.code, email.body)
        self.assertTrue(any(ticket.code in html for html in [email.alternatives[0][0]]))

        with self.captureOnCommitCallbacks(execute=True):
            order, fulfilled_now = verify_and_fulfill(
                order, transaction_for(order)
            )
        self.assertFalse(fulfilled_now)
        self.assertEqual(order.tickets.count(), 2)
        self.assertEqual(len(mail.outbox), 1)

    def test_amount_mismatch_is_rejected(self):
        with self.assertRaises(PaymentError):
            verify_and_fulfill(
                self.order, transaction_for(self.order, amount=100_000)
            )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.tickets.count(), 0)

    def test_currency_mismatch_is_rejected(self):
        with self.assertRaises(PaymentError):
            verify_and_fulfill(
                self.order, transaction_for(self.order, currency="USD")
            )
        self.assertEqual(self.order.tickets.count(), 0)

    def test_unsuccessful_transaction_is_rejected(self):
        with self.assertRaises(PaymentError):
            verify_and_fulfill(
                self.order, transaction_for(self.order, status="failed")
            )
        self.assertEqual(self.order.tickets.count(), 0)

    def test_callback_requires_authentication(self):
        response = self.client.get(
            reverse("orders:callback"), {"reference": self.order.reference}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response.url)

    @patch("orders.services.paystack.verify_transaction")
    def test_callback_verifies_and_fulfills(self, verify):
        verify.return_value = transaction_for(self.order)
        self.client.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.get(
                reverse("orders:callback"), {"reference": self.order.reference}
            )
        self.assertRedirects(
            response,
            reverse("orders:detail", args=[self.order.access_token]),
            fetch_redirect_response=False,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.order.tickets.count(), 2)

    @patch("orders.services.paystack.verify_transaction")
    def test_callback_cannot_touch_another_users_order(self, verify):
        other = get_user_model().objects.create_user(
            username="other", email="other@example.com", password="Strong-pass-123!"
        )
        verify.return_value = transaction_for(self.order)
        self.client.force_login(other)
        response = self.client.get(
            reverse("orders:callback"), {"reference": self.order.reference}
        )
        self.assertRedirects(
            response, reverse("orders:account"), fetch_redirect_response=False
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        verify.assert_not_called()

    def test_order_detail_is_private(self):
        other = get_user_model().objects.create_user(
            username="other", email="other@example.com", password="Strong-pass-123!"
        )
        url = reverse("orders:detail", args=[self.order.access_token])
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_verify_endpoint_is_post_only(self):
        self.client.force_login(self.user)
        url = reverse("orders:verify", args=[self.order.access_token])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_order_page_shows_codes_after_payment(self):
        self.order.status = Order.Status.PAID
        self.order.paid_at = timezone.now()
        self.order.save()
        Ticket.objects.create(
            order=self.order,
            event=self.event,
            sequence=0,
            attendee_name=self.order.full_name,
            attendee_email=self.order.email,
        )
        Ticket.objects.create(
            order=self.order,
            event=self.event,
            sequence=1,
            attendee_name=self.order.full_name,
            attendee_email=self.order.email,
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("orders:detail", args=[self.order.access_token])
        )
        self.assertEqual(response.status_code, 200)
        for ticket in self.order.tickets.all():
            self.assertContains(response, ticket.code)


@override_settings(**PAYSTACK_SETTINGS)
class WebhookTests(TestCase):
    def setUp(self):
        self.event = Event.objects.get(slug="creative-rebirth-live")
        self.order = Order.objects.create(
            event=self.event,
            full_name="Ada Buyer",
            email="ada@example.com",
            quantity=1,
            unit_price_kobo=100_000,
            total_kobo=100_000,
        )
        self.url = reverse("orders:webhook")

    def _post(self, payload, signature=None):
        body = json.dumps(payload)
        if signature is None:
            signature = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode(),
                body.encode(),
                hashlib.sha512,
            ).hexdigest()
        return self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def test_rejects_bad_signature(self):
        response = self._post(
            {"event": "charge.success", "data": transaction_for(self.order)},
            signature="nope",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.order.tickets.count(), 0)

    def test_rejects_missing_signature(self):
        response = self.client.post(
            self.url,
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_charge_success_issues_tickets(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self._post(
                {
                    "event": "charge.success",
                    "data": transaction_for(self.order),
                }
            )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.order.tickets.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_charge_success_is_idempotent(self):
        payload = {"event": "charge.success", "data": transaction_for(self.order)}
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self._post(payload).status_code, 200)
            self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(self.order.tickets.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_ignores_unknown_reference(self):
        data = transaction_for(self.order, reference="CRL-UNKNOWN")
        response = self._post({"event": "charge.success", "data": data})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_ignores_non_success_events(self):
        response = self._post(
            {"event": "transfer.success", "data": transaction_for(self.order)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.order.tickets.count(), 0)

    def test_amount_mismatch_does_not_issue_tickets(self):
        data = transaction_for(self.order, amount=1)
        response = self._post({"event": "charge.success", "data": data})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(self.order.tickets.count(), 0)
