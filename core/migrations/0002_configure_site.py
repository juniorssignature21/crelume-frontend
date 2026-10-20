"""Point allauth's Site at the configured public URL."""

from urllib.parse import urlparse

from django.conf import settings
from django.db import migrations


def configure_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    host = urlparse(settings.SITE_URL).netloc or "localhost:8080"
    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": host, "name": "Crelume"},
    )


def unconfigure_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(pk=settings.SITE_ID).update(
        domain="example.com", name="example.com"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(configure_site, unconfigure_site),
    ]
