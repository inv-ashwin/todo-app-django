from django.db import models
from django.utils import timezone

class Task(models.Model):
    STATUS_CHOICES = [
        ("Not Started", "Not Started"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
    ]

    task = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Not Started"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    position = models.IntegerField(default=0)

    def duration(self):
        if self.status == "Completed" and self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return str(delta).split(".")[0]
        return "-"

    def __str__(self):
        return self.task

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "created_at"],
                name="unique_task_created_time"
            )
        ]

class SyncStatus(models.Model):
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Last synced at {self.last_synced_at}"
