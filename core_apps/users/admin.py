from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core_apps.profiles.models import Profile

from .forms import UserChangeForm, UserCreationForm

User = get_user_model()


class ODKRoleFilter(admin.SimpleListFilter):
    title = _("ODK Role")
    parameter_name = "odk_role"

    def lookups(self, request, model_admin):
        # Get distinct ODK roles and sort them alphabetically
        odk_roles = (
            Profile.objects.exclude(odk_role__isnull=True)
            .exclude(odk_role__exact="")
            .values_list("odk_role", flat=True)
            .distinct()
            .order_by("odk_role")
        )

        # Convert to list of tuples for admin interface
        return [(str(role), str(role)) for role in odk_roles]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile__odk_role=self.value())
        return queryset


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "User Profile"
    fk_name = "user"
    readonly_fields = [
        "avatar_preview",
    ]

    def avatar_preview(self, instance):
        if instance.avatar:
            return format_html(
                '<img src="{}" width="300" height="300" style="object-fit: cover;" />',
                instance.avatar.url,
            )
        return "No avatar"

    avatar_preview.short_description = "Preview"

    fieldsets = (
        ("", {"fields": ("avatar_preview", "avatar")}),
        (
            "",
            {
                "fields": (
                    "gender",
                    "odk_role",
                    "bio",
                    "phone_number",
                    "country_of_origin",
                    "city_of_origin",
                )
            },
        ),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = (ProfileInline,)
    list_filter = ("is_superuser", "is_active", ODKRoleFilter)
    # Pagination settings
    list_per_page = 5  # Nombre d'éléments par page
    list_max_show_all = 1000  # Nombre maximum d'éléments quand "Show all" est cliqué
    show_full_result_count = True  # Afficher le nombre total d'éléments

    list_display = [
        "pkid",
        "id",
        "email",
        "avatar",
        "first_name",
        "last_name",
        "username",
        "is_superuser",
        "get_gender",
        "get_odk_role",
    ]
    list_display_links = ["pkid", "id", "email"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["pkid"]
    list_select_related = ("profile",)

    def avatar(self, instance):
        if instance.profile.avatar:
            width, height = 60, 60  # Set desired width and height
            return format_html(
                '<img src="{}" width="{}" height="{}" style="border-radius: 50%; object-fit: cover;" />',
                instance.profile.avatar.url,
                width,
                height,
            )
        return "No avatar"

    def get_gender(self, instance):
        return instance.profile.gender

    get_gender.short_description = "Gender"

    def get_odk_role(self, instance):
        return instance.profile.odk_role

    get_odk_role.short_description = "ODK Role"

    fieldsets = (
        (_("Login Credentials"), {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "username")}),
        (
            _("Permissions and Groups"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    # filter user list by ODK role

    def get_inline_instances(self, request, obj=None):
        return super(UserAdmin, self).get_inline_instances(request, obj) if obj else []
