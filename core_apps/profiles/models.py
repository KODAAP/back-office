from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from core_apps.common.models import TimeStampedModel

User = get_user_model()


def avatar_upload_path(instance, filename="photo"):
    """Génère le chemin pour l'avatar"""
    return "avatars/{0}_{1}".format(instance.user.email, "photo")


class Profile(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = (
            "male",
            _("Male"),
        )
        FEMALE = (
            "female",
            _("Female"),
        )
        OTHER = (
            "other",
            _("Other"),
        )

    class ODKRole(models.TextChoices):
        # DATA_COLLECTOR = (
        #     "data_collector",
        #     _("Data Collector"),
        # )
        INSUCO_USER = (
            "insuco_user",
            _("Insuco User"),
        )
        MANAGER = (
            "manager",
            _("Project Manager"),
        )
        ADMINISTRATOR = (
            "administrator",
            _("Administrator"),
        )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        verbose_name=_("Avatar"),
        upload_to=avatar_upload_path,
        storage=FileSystemStorage(),
        blank=True,
        null=True,
        default="avatars/default-avatar.png",
    )
    gender = models.CharField(
        verbose_name=_("Gender"),
        max_length=10,
        choices=Gender.choices,
        default=Gender.OTHER,
    )
    bio = models.TextField(verbose_name=_("Bio"), blank=True, null=True)
    odk_role = models.CharField(
        verbose_name=_("ODK Role"),
        max_length=20,
        choices=ODKRole.choices,
        default=ODKRole.INSUCO_USER,
    )
    phone_number = PhoneNumberField(
        verbose_name=_("Phone Number"), max_length=30, default="+250784123456"
    )
    country_of_origin = CountryField(verbose_name=_("Country"), default="KE")
    city_of_origin = models.CharField(
        verbose_name=_("City"), max_length=180, default="Nairobi"
    )

    def __str__(self) -> str:
        return f"{self.user.first_name}'s Profile"

    def get_avatar_url(self):
        """Retourne l'URL de l'avatar"""
        if self.avatar:
            return self.avatar.url
        return None
