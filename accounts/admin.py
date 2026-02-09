from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "display_name", "masked_email", "is_staff")
    search_fields = ("username", "display_name")
    readonly_fields = ("id",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Privacy", {"fields": ("display_name",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Privacy", {"fields": ("display_name",)}),
    )
