from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactMessage


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ContactFormTests(TestCase):
    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    def test_contact_message_is_saved_and_emailed(self, _captcha):
        response = self.client.post(
            reverse("core:contact"),
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "about": "Partnership",
                "message": "Let's build something together.",
                "g-recaptcha-response": "test",
            },
        )
        self.assertRedirects(
            response, "/#contact", fetch_redirect_response=False
        )
        message = ContactMessage.objects.get()
        self.assertEqual(message.email, "ada@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("ada@example.com", mail.outbox[0].body)
        self.assertIn("Let's build something together.", mail.outbox[0].body)

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    def test_invalid_contact_form_is_not_saved(self, _captcha):
        response = self.client.post(
            reverse("core:contact"),
            {
                "name": "Ada Lovelace",
                "email": "not-an-email",
                "about": "Hello",
                "message": "",
                "g-recaptcha-response": "test",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_endpoint_is_post_only(self):
        self.assertEqual(self.client.get(reverse("core:contact")).status_code, 405)


class PagesTests(TestCase):
    def test_health_check_reports_ok(self):
        response = self.client.get(reverse("core:healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "ok", "database": "ok"}
        )

    def test_health_check_is_get_only(self):
        self.assertEqual(
            self.client.post(reverse("core:healthz")).status_code, 405
        )

    def test_home_renders_events_and_recaptcha(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Creative Rebirth: Live")
        self.assertContains(response, "g-recaptcha")
        self.assertContains(response, 'name="email"')

    def test_event_detail_renders(self):
        response = self.client.get(
            reverse("events:detail", args=["creative-rebirth-live"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Creative Rebirth: Live")
        self.assertContains(response, "Buy tickets")

    def test_unknown_event_returns_404(self):
        response = self.client.get(reverse("events:detail", args=["nope"]))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page moved on.", status_code=404)

    def test_auth_pages_include_captcha(self):
        for name in ["account_login", "account_signup"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "g-recaptcha")

    def test_checkout_page_requires_login_then_renders_captcha(self):
        user = get_user_model().objects.create_user(
            username="buyer", email="buyer@example.com", password="Strong-pass-123!"
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("orders:checkout", args=["creative-rebirth-live"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "g-recaptcha")
        self.assertContains(response, "Paystack")

    def test_free_online_event_has_no_checkout(self):
        response = self.client.get(reverse("events:detail", args=["before-creative-rebirth"]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Buy tickets")


class SignupTests(TestCase):
    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    def test_signup_creates_unverified_user_and_sends_email(self, _captcha):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "new@example.com",
                "username": "newdesigner",
                "password1": "A-strong-password-42!",
                "password2": "A-strong-password-42!",
                "g-recaptcha-response": "test",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email="new@example.com")
        self.assertFalse(user.emailaddress_set.get(email="new@example.com").verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("http://testserver/accounts/confirm-email/", mail.outbox[0].body)

    @patch("django_recaptcha.fields.ReCaptchaField.validate", return_value=None)
    def test_signup_rejects_mismatched_passwords(self, _captcha):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "new@example.com",
                "username": "newdesigner",
                "password1": "A-strong-password-42!",
                "password2": "Different-password-42!",
                "g-recaptcha-response": "test",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 0)
