from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path(
        "events/<slug:slug>/tickets/",
        views.CheckoutView.as_view(),
        name="checkout",
    ),
    path("account/", views.AccountView.as_view(), name="account"),
    path("orders/<uuid:token>/", views.OrderDetailView.as_view(), name="detail"),
    path(
        "orders/<uuid:token>/verify/",
        views.VerifyPaymentView.as_view(),
        name="verify",
    ),
    path(
        "payments/paystack/callback/",
        views.PaystackCallbackView.as_view(),
        name="callback",
    ),
    path("payments/paystack/webhook/", views.paystack_webhook, name="webhook"),
]
