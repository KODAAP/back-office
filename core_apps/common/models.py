import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class TimeStampedModel(models.Model):
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at", "-updated_at"]


class AuditLogs(TimeStampedModel):
    class Resources(models.TextChoices):
        PROJECT = (
            "project",
            _("Project"),
        )
        FORM = (
            "form",
            _("Form"),
        )
        SUBMISSION = (
            "submission",
            _("Submission"),
        )
        USER = (
            "user",
            _("User"),
        )

    resource_type = models.CharField(
        verbose_name="Resource Type",
        max_length=30,
        choices=Resources.choices,
        default=None,
    )
    # Identifies the specific resource instance affected (e.g., the ID of a project or user)
    resource_id = models.CharField(verbose_name="Resource ID")
    details = models.JSONField(verbose_name="Details")
    success = models.BooleanField(default=True, verbose_name="Success")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="User", related_name="odk_logs"
    )
    action = models.CharField(verbose_name="Action", max_length=100)
    ip_address = models.GenericIPAddressField(
        verbose_name="IP Address", null=True, blank=True
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self) -> str:
        status = "succeeded" if self.success else "failed"
        return f"{self.action} ({self.resource_type}) par {self.user.get_full_name} - {status}"
