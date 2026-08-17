import uuid
from django.db import models
from django.utils import timezone

class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft delete all items in the queryset."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Actually delete the items from the database."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        """By default, return only records that are not soft-deleted."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    # Public-facing UUID
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Auditing fields (using string relations to avoid circular dependencies)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_by'
    )
    updated_by = models.ForeignKey(
        'core.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated_by'
    )

    # Soft delete field
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """Perform soft delete by setting deleted_at timestamp."""
        self.deleted_at = timezone.now()
        # Save only the fields that were modified to avoid side effects
        self.save(update_fields=['deleted_at', 'updated_at'])

    def hard_delete(self, *args, **kwargs):
        """Actually delete the record from database."""
        super().delete(*args, **kwargs)


class CompanyScopedModel(BaseModel):
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='%(class)s_records'
    )

    class Meta:
        abstract = True
