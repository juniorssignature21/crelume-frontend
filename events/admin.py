from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "date_label",
        "is_ticketed",
        "formatted_price",
        "capacity",
        "tickets_sold",
        "is_active",
    )
    list_filter = ("is_ticketed", "is_featured", "is_online", "is_active")
    search_fields = ("name", "location", "venue", "platform")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("tickets_sold", "created_at", "updated_at")
