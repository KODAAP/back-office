from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core_apps.common.models import TimeStampedModel

User = get_user_model()


class ODKUserSessions(TimeStampedModel):
    odk_token = models.CharField(verbose_name="Odk Token")
    token_expired_at = models.DateTimeField(verbose_name="Odk Token Expired", null=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, verbose_name="Sycosur User"
    )
    actor_id = models.BigIntegerField(verbose_name="Odk Actor ID", null=True)

    class Meta:
        db_table = "odk_user_sessions"
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self) -> str:
        return f"{self.user.email} Session"

    def is_valid(self) -> bool:
        if self.token_expired_at is None:
            return False
        return self.token_expired_at > timezone.now()


class Export(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "En cours"
        READY = "ready", "Prêt"
        ERROR = "error", "Erreur"

    class ExportType(models.TextChoices):
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"
        ZIP = "zip", "ZIP Médias"
        SHP = "shp", "Shapefile"

    odk_project_id = models.IntegerField()
    form_id = models.CharField(max_length=255)
    export_type = models.CharField(max_length=10, choices=ExportType.choices)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    file_data = models.BinaryField(null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    options = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export {self.export_type} {self.form_id} - {self.status}"
