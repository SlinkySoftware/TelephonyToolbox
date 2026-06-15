from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from access_groups.models import AccessGroup
from telephony_toolbox.models import UUIDTimestampedModel


class Diversion(UUIDTimestampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source_number = models.CharField(max_length=64, unique=True)
    source_partition = models.CharField(max_length=255, default=settings.CUCM_ROUTE_PARTITION)
    cached_current_destination = models.CharField(max_length=255, blank=True, default='')
    group = models.ForeignKey(AccessGroup, on_delete=models.PROTECT, related_name='diversions')
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    last_updated_at = models.DateTimeField(null=True, blank=True)
    last_updated_by_text = models.CharField(max_length=255, blank=True, default='')
    created_by_text = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)

    def clean(self):
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).values_list('source_number', flat=True).first()
            if original and original != self.source_number:
                raise ValidationError({'source_number': 'Source number cannot be changed after creation.'})

    def __str__(self):
        return f'{self.name} ({self.source_number})'