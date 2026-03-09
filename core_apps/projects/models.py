from django.contrib.auth import get_user_model
from django.db import models

from core_apps.common.models import TimeStampedModel

User = get_user_model()


class Projects(TimeStampedModel):
    odk_id = models.BigIntegerField(
        unique=True, verbose_name="ODK Project ID", null=True
    )
    name = models.CharField(
        max_length=150, verbose_name="Project name", unique=True, null=False
    )
    description = models.TextField(null=True, verbose_name="Description")
    deleted = models.BooleanField(default=False, verbose_name="Deleted", null=True)
    deleted_at = models.DateTimeField(null=True, verbose_name="Deleted at")
    archived = models.BooleanField(default=False, verbose_name="Archived", null=True)
    archived_at = models.DateTimeField(null=True, verbose_name="Archived at")
    last_sync = models.DateTimeField(
        auto_now=True, verbose_name="Last synchronization", null=True
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Created by",
        related_name="owner",
    )

    class Meta:
        db_table = "projects"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        ordering = ["-created_at", "name"]
        permissions = [
            ("access_project", "Can access project"),
            ("archive_project", "Can archive project"),
            ("restore_project", "Can restore project"),
            ("manage_project", "Can manage project"),
            ("view_form", "Can view ODK form"),
            ("create_form", "Can create ODK form"),
            ("edit_form", "Can edit ODK form"),
            ("delete_form", "Can delete ODK form"),
            # ("download_form", "Can download ODK form"),
            ("view_submission", "Can view submission"),
            ("add_submission", "Can create submission"),
            ("edit_submission", "Can edit submission"),
            ("delete_submission", "Can delete submission"),
        ]

    def __str__(self) -> str:
        return self.name
