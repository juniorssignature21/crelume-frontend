"""Seed the two events shown in the original design."""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

LAGOS = ZoneInfo("Africa/Lagos")


def seed_events(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Event.objects.update_or_create(
        slug="creative-rebirth-live",
        defaults={
            "name": "Creative Rebirth: Live",
            "kicker": "Creative Rebirth: Live",
            "season": "Season 01",
            "tagline": "There is still more.",
            "wordmark": "UNFINISHED",
            "date_label": "12 Dec 2026.",
            "time_label": "Doors open 4:00 PM WAT",
            "location": "Aba, Abia state",
            "venue": "Outdoor",
            "platform": "",
            "description": (
                "One afternoon, one room, and a community of designers choosing to begin "
                "again. Creative Rebirth: Live brings conversations, live work and the "
                "people who make Crelume what it is together in Aba."
            ),
            "starts_at": datetime(2026, 12, 12, 16, 0, tzinfo=LAGOS),
            "price_kobo": 100_000,
            "capacity": 300,
            "is_ticketed": True,
            "is_featured": True,
            "is_online": False,
            "is_active": True,
            "filter_tags": "live upcoming",
        },
    )
    Event.objects.update_or_create(
        slug="before-creative-rebirth",
        defaults={
            "name": "Before Creative Rebirth",
            "kicker": "Conversation for People\nBecoming More",
            "season": "",
            "tagline": "",
            "wordmark": "BEFORE CREATIVE REBIRTH",
            "date_label": "Saturdays . 3rd Oct – 7th Nov",
            "time_label": "8:00 PM WAT",
            "location": "Online",
            "venue": "",
            "platform": "Google meet",
            "description": (
                "A six-week online series of honest conversations for designers who are "
                "still becoming. We meet on Google Meet every Saturday at 8:00 PM WAT, "
                "3rd October through 7th November."
            ),
            "starts_at": datetime(2026, 10, 3, 20, 0, tzinfo=LAGOS),
            "price_kobo": 0,
            "capacity": None,
            "is_ticketed": False,
            "is_featured": False,
            "is_online": True,
            "is_active": True,
            "filter_tags": "online upcoming",
        },
    )


def unseed_events(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Event.objects.filter(
        slug__in=["creative-rebirth-live", "before-creative-rebirth"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_events, unseed_events),
    ]
