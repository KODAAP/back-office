from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _


def validate_email_address(email: str):
    try:
        validate_email(email)
    except ValidationError:
        raise ValidationError(_("Enter a valid email address")) from None


class UserManager(DjangoUserManager):
    def _create_user(
        self,
        email: str,
        password: str | None,
        username: str | None = None,
        **extra_fields,
    ):
        if not email:
            raise ValueError(_("An email address must be provided"))
        email = self.normalize_email(email)
        validate_email_address(email)

        # Si username est fourni, le normaliser
        if username:
            global_user_model = apps.get_model(
                self.model._meta.app_label, self.model._meta.object_name
            )
            username = global_user_model.normalize_username(username)

        user = self.model(email=email, username=username, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        username: str | None = None,
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, username, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        username: str | None = None,
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))

        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        try:
            existing_user = self.model.objects.get(email=email)
            # Si l'utilisateur existe, mettre à jour les champs et retourner
            existing_user.is_staff = True
            existing_user.is_superuser = True
            if password:
                existing_user.set_password(password)
            existing_user.save()
            return existing_user
        except self.model.DoesNotExist:
            # Si l'utilisateur n'existe pas, en créer un nouveau
            return self._create_user(email, password, username, **extra_fields)
