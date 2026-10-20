from django.contrib import admin

from .models import Order, Ticket


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    can_delete = False
    readonly_fields = (
        "sequence",
        "code",
        "attendee_name",
        "attendee_email",
        "issued_at",
        "checked_in_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "event",
        "email",
        "quantity",
        "formatted_total",
        "status",
        "created_at",
    )
    list_filter = ("status", "event", "created_at")
    search_fields = ("reference", "email", "full_name", "gateway_reference")
    date_hierarchy = "created_at"
    inlines = [TicketInline]
    readonly_fields = (
        "reference",
        "access_token",
        "user",
        "event",
        "full_name",
        "email",
        "quantity",
        "unit_price_kobo",
        "total_kobo",
        "currency",
        "status",
        "gateway_reference",
        "gateway_response",
        "paid_at",
        "email_sent_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("code", "event", "order", "attendee_email", "issued_at", "checked_in_at")
    list_filter = ("event", "checked_in_at")
    search_fields = ("code", "order__reference", "attendee_email", "attendee_name")
    readonly_fields = (
        "order",
        "event",
        "sequence",
        "code",
        "attendee_name",
        "attendee_email",
        "issued_at",
        "checked_in_at",
    )

    def has_add_permission(self, request):
        return False
