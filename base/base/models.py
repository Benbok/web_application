from django.db import models
from django.utils import timezone

class ArchivableModel(models.Model):
    is_archived = models.BooleanField(default=False, verbose_name="Архивировано")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата архивации")

    class Meta:
        abstract = True

    def archive(self):
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=["is_archived", "archived_at"])

    def delete(self, *args, **kwargs):
        self.archive()

class NotArchivedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_archived=False) 