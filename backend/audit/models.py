# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.db import models

from telephony_toolbox.models import UUIDModel


class AuditResult(models.TextChoices):
    SUCCESS = 'success', 'Success'
    FAILURE = 'failure', 'Failure'
    WARNING = 'warning', 'Warning'


class AuditEvent(UUIDModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=128)
    result = models.CharField(max_length=16, choices=AuditResult.choices)
    actor_user_id_text = models.CharField(max_length=64, blank=True, default='')
    actor_email = models.CharField(max_length=255, blank=True, default='')
    actor_display_name = models.CharField(max_length=255, blank=True, default='')
    actor_auth_source = models.CharField(max_length=32, blank=True, default='')
    object_type = models.CharField(max_length=64, blank=True, default='')
    object_id_text = models.CharField(max_length=64, blank=True, default='')
    object_name = models.CharField(max_length=255, blank=True, default='')
    source_number = models.CharField(max_length=64, blank=True, default='')
    destination_number = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f'{self.timestamp.isoformat()} {self.event_type}'