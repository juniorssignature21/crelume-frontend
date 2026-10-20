from django import forms
from django.conf import settings
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


class CheckoutForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=settings.TICKET_MAX_QUANTITY,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                "min": 1,
                "max": settings.TICKET_MAX_QUANTITY,
                "inputmode": "numeric",
                "class": "input",
                "id": "id_quantity",
                "autocomplete": "off",
            }
        ),
        error_messages={
            "min_value": "Choose at least one ticket.",
            "max_value": "You can buy up to %(limit_value)s tickets at a time.",
            "required": "Choose how many tickets you need.",
            "invalid": "Enter a whole number of tickets.",
        },
    )
    full_name = forms.CharField(
        max_length=120,
        label="Full name",
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "autocomplete": "name",
                "placeholder": "Name on the tickets",
                "required": True,
            }
        ),
    )
    email = forms.EmailField(
        label="Ticket email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "placeholder": "Where your tickets should go",
                "required": True,
            }
        ),
        help_text="We'll email your tickets here after payment.",
    )
    captcha = ReCaptchaField(
        label="I'm not a robot",
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"}),
    )

    def clean_full_name(self):
        return self.cleaned_data["full_name"].strip()
