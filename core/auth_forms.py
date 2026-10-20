"""allauth forms extended with reCAPTCHA v2."""

from allauth.account.forms import LoginForm, SignupForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


class CaptchaLoginForm(LoginForm):
    captcha = ReCaptchaField(
        label="I'm not a robot",
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"}),
    )


class CaptchaSignupForm(SignupForm):
    captcha = ReCaptchaField(
        label="I'm not a robot",
        widget=ReCaptchaV2Checkbox(attrs={"data-theme": "dark"}),
    )
