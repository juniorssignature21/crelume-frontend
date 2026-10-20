from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "about", "created_at")
    search_fields = ("name", "email", "about", "message")
    readonly_fields = ("name", "email", "about", "message", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False
