from django.contrib import admin

from .models import Claim, Item, Message


class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 0
    readonly_fields = ("id", "seeker", "status", "created_at")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("id", "sender", "body", "created_at")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "neighborhood", "status", "created_at")
    list_filter = ("status", "category", "city")
    search_fields = ("title", "description", "neighborhood")
    readonly_fields = ("id", "handshake_uuid", "qr_code", "created_at", "updated_at")
    inlines = [ClaimInline]


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("item", "seeker", "status", "created_at")
    list_filter = ("status",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "sender", "created_at")
    readonly_fields = ("id", "created_at")
