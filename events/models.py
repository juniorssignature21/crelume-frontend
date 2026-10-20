from django.db import models
from django.urls import reverse
from django.utils import timezone


class Event(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    kicker = models.CharField(
        max_length=80, blank=True, help_text="Small label above the title, e.g. Featured."
    )
    season = models.CharField(
        max_length=60, blank=True, help_text="Optional season label, e.g. Season 01."
    )
    tagline = models.CharField(
        max_length=160, blank=True, help_text="Short line shown beside the event card."
    )
    wordmark = models.CharField(
        max_length=80,
        blank=True,
        help_text="Large display word on the event card, e.g. UNFINISHED.",
    )
    date_label = models.CharField(max_length=120, help_text="Human-friendly date, e.g. 12th Dec 2026.")
    time_label = models.CharField(max_length=80, blank=True)
    location = models.CharField(
        max_length=200, help_text="Venue name or platform, e.g. Vibes on the Island."
    )
    venue = models.CharField(max_length=200, blank=True)
    platform = models.CharField(max_length=120, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    filter_tags = models.CharField(
        max_length=120,
        blank=True,
        default="upcoming",
        help_text="Space-separated filter tags: upcoming past live online.",
    )
    price_kobo = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(
        null=True, blank=True, help_text="Leave blank for unlimited tickets."
    )
    is_ticketed = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]
        indexes = [models.Index(fields=["is_active", "is_featured"])]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("events:detail", kwargs={"slug": self.slug})

    @property
    def price_naira(self):
        return self.price_kobo // 100

    @property
    def formatted_price(self):
        return "Free" if self.price_kobo == 0 else f"₦{self.price_naira:,}"

    @property
    def tickets_sold(self):
        return self.tickets.count()

    @property
    def tickets_remaining(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.tickets_sold, 0)

    @property
    def is_sold_out(self):
        return self.tickets_remaining == 0

    @property
    def is_on_sale(self):
        if not (self.is_active and self.is_ticketed and self.price_kobo > 0):
            return False
        if self.is_sold_out:
            return False
        if self.starts_at and self.starts_at <= timezone.now():
            return False
        return True
