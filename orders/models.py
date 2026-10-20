import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from events.models import Event


def generate_reference():
    return f"CRL-{uuid.uuid4().hex.upper()}"


def generate_ticket_code():
    return f"CRL-{uuid.uuid4().hex[:12].upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_orders",
    )
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="orders")
    reference = models.CharField(
        max_length=64, unique=True, default=generate_reference, editable=False
    )
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price_kobo = models.PositiveIntegerField()
    total_kobo = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    gateway_reference = models.CharField(max_length=120, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "event"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1), name="order_quantity_at_least_one"
            ),
            models.CheckConstraint(
                condition=models.Q(total_kobo__gte=0), name="order_total_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.reference} — {self.event.name} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("orders:detail", kwargs={"token": self.access_token})

    @property
    def total_naira(self):
        return self.total_kobo // 100

    @property
    def formatted_total(self):
        return f"₦{self.total_naira:,}"

    @property
    def can_verify(self):
        return self.status == self.Status.PENDING

    @property
    def is_paid(self):
        return self.status == self.Status.PAID


class Ticket(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="tickets")
    sequence = models.PositiveSmallIntegerField()
    code = models.CharField(
        max_length=32, unique=True, default=generate_ticket_code, editable=False
    )
    attendee_name = models.CharField(max_length=120, blank=True)
    attendee_email = models.EmailField(blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "sequence"], name="unique_ticket_sequence_per_order"
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.event.name}"

    @property
    def is_checked_in(self):
        return self.checked_in_at is not None
