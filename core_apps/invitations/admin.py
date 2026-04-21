from django.contrib import admin

from core_apps.invitations.models import UserInvitation


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "invited_by",
        "created_at",
        "expires_at",
        "is_used",
        "used_at",
    ]
    list_filter = ["is_used", "created_at", "expires_at"]
    search_fields = ["email", "invited_by__email"]
    readonly_fields = ["token", "created_at", "used_at"]
    date_hierarchy = "created_at"
