import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core_apps.common.models import TimeStampedModel
from core_apps.common.tasks import send_email_task
from core_apps.users.models import User


class UserInvitation(TimeStampedModel):
    """Modèle pour gérer les invitations d'utilisateurs"""

    email = models.EmailField(verbose_name=_("Email Address"), db_index=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_invitations"
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("User Invitation")
        verbose_name_plural = _("User Invitations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation for {self.email}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Vérifie si l'invitation est valide"""
        return not self.is_used and self.expires_at > timezone.now()

    def mark_as_used(self):
        """Marque l'invitation comme utilisée"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

    def send_invitation_email(self):
        """Envoyer l'email d'invitation"""
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8080")
        site_name = getattr(settings, "SITE_NAME", "Sycosur")
        invitation_link = (
            f"{frontend_url}/register?token={self.token}&email={self.email}"
        )

        context = {
            "invited_by": self.invited_by.get_full_name,
            "site_name": site_name,
            "invitation_link": invitation_link,
            "email": self.email,
            "current_year": timezone.now().year,
        }

        html_message = render_to_string("emails/invitation.html", context)
        plain_message = f"""
            Bonjour,

            {self.invited_by.get_full_name} vous invite à rejoindre {site_name}.

            Cliquez sur ce lien pour créer votre compte :
            {invitation_link}

            Ce lien expirera dans 7 jours.

            Cordialement,
            L'équipe {site_name}
        """

        send_email_task.delay(
            subject=f"Invitation à rejoindre {site_name}",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            html_message=html_message,
            fail_silently=False,
        )
