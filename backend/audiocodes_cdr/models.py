# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.conf import settings
from django.db import models

from audiocodes_cdr.constants import MEDIA_QUALITY_METRICS, USER_DEFINED_FIELD_KEYS
from audiocodes_cdr.source_models import Cdr, Sdr  # noqa: F401  registers the unmanaged source models
from telephony_toolbox.models import TimestampedModel, UUIDTimestampedModel


class SourceRole(models.TextChoices):
    REPLICA = 'replica', 'Read replica'
    PRIMARY = 'primary', 'Primary'


class SslMode(models.TextChoices):
    DISABLE = 'disable', 'disable'
    PREFER = 'prefer', 'prefer'
    REQUIRE = 'require', 'require'
    VERIFY_CA = 'verify-ca', 'verify-ca'
    VERIFY_FULL = 'verify-full', 'verify-full'


class DurationFormat(models.TextChoices):
    SECONDS = 'seconds', 'Decimal seconds'
    HMS = 'hms', 'HH:MM:SS.ff'


def default_media_quality():
    return {metric: {'warning': None, 'critical': None, 'unit': ''} for metric in MEDIA_QUALITY_METRICS}


def default_user_defined_fields():
    return {key: {'label': f'User Defined {index}', 'description': ''} for index, key in enumerate(USER_DEFINED_FIELD_KEYS, start=1)}


class CdrSourceProfile(UUIDTimestampedModel):
    role = models.CharField(max_length=16, choices=SourceRole.choices, unique=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=5432)
    database_name = models.CharField(max_length=63)
    username = models.CharField(max_length=63)
    password_encrypted = models.TextField(blank=True, default='')
    sslmode = models.CharField(max_length=16, choices=SslMode.choices, default=SslMode.PREFER)
    sslrootcert = models.CharField(max_length=1024, blank=True, default='')
    connect_timeout = models.PositiveSmallIntegerField(default=10)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ('role',)

    def __str__(self):
        return f'AudioCodes source ({self.role})'


class CdrModuleSettings(TimestampedModel):
    SINGLETON_ID = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=SINGLETON_ID, editable=False)
    active_source = models.CharField(max_length=16, choices=SourceRole.choices, default=SourceRole.REPLICA)
    max_page_size = models.PositiveIntegerField(default=500)
    max_multiselect_values = models.PositiveIntegerField(default=50)
    lookup_cache_seconds = models.PositiveIntegerField(default=900)
    statistics_cache_seconds = models.PositiveIntegerField(default=300)
    termination_lookup_days = models.PositiveIntegerField(default=30)
    hourly_bucket_max_hours = models.PositiveIntegerField(default=168)
    user_defined_fields = models.JSONField(default=default_user_defined_fields, blank=True)
    media_quality = models.JSONField(default=default_media_quality, blank=True)
    field_help_overrides = models.JSONField(default=dict, blank=True)
    # Bumped on every change so other workers/threads drop cached connections and lookups.
    config_version = models.PositiveIntegerField(default=1)
    updated_by_text = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        verbose_name = 'AudioCodes CDR module settings'

    def __str__(self):
        return 'AudioCodes CDR module settings'

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_ID
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        return obj


class CdrUserPreference(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cdr_preference')
    duration_format = models.CharField(max_length=16, choices=DurationFormat.choices, default=DurationFormat.HMS)

    def __str__(self):
        return f'CDR preferences for {self.user_id}'
