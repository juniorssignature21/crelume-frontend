from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    captcha = ReCaptchaField(
        label="I'm not a robot",
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"}),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "about", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Your name",
                    "autocomplete": "name",
                    "class": "input",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Your email",
                    "autocomplete": "email",
                    "class": "input",
                    "required": True,
                }
            ),
            "about": forms.TextInput(
                attrs={
                    "placeholder": "What's this about ?",
                    "class": "input",
                    "required": True,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "placeholder": "Your message",
                    "class": "input input--area",
                    "required": True,
                }
            ),
        }
        error_messages = {
            "name": {"required": "Please tell us your name."},
            "email": {"required": "Please add an email so we can reply."},
            "about": {"required": "Let us know what this is about."},
            "message": {"required": "Please write a message."},
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_about(self):
        return self.cleaned_data["about"].strip()

    def clean_message(self):
        return self.cleaned_data["message"].strip()
