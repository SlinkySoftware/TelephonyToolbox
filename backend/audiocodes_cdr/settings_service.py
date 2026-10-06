# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Module settings persistence. Credentials are encrypted before storage and never returned or audited."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from audit.services import AuditService
from audiocodes_cdr.constants import (
    DEFAULT_PAGE_SIZE,
    MATCH_MODES,
    MAX_RANGE_MONTHS,
    MEDIA_QUALITY_METRICS,
    PAGE_SIZE_OPTIONS,
    STATUS_FILTERS,
)
from audiocodes_cdr.crypto import KEY_OK, encrypt_secret, key_status
from audiocodes_cdr.field_help import build_field_help
from audiocodes_cdr.models import (
    CdrModuleSettings,
    CdrSourceProfile,
    CdrUserPreference,
    DurationFormat,
    SourceRole,
    default_media_quality,
    default_user_defined_fields,
)
from audiocodes_cdr.search import SORT_FIELDS
from audiocodes_cdr.timeutils import PRESETS

SCALAR_FIELDS = (
    'active_source',
    'max_page_size',
    'max_multiselect_values',
    'lookup_cache_seconds',
    'statistics_cache_seconds',
    'termination_lookup_days',
    'hourly_bucket_max_hours',
)
JSON_FIELDS = ('user_defined_fields', 'media_quality', 'field_help_overrides')
PROFILE_FIELDS = ('host', 'port', 'database_name', 'username', 'sslmode', 'sslrootcert', 'connect_timeout', 'is_enabled')


def page_size_options(module_settings):
    return [size for size in PAGE_SIZE_OPTIONS if size <= module_settings.max_page_size]


def default_page_size(module_settings):
    options = page_size_options(module_settings)
    return DEFAULT_PAGE_SIZE if DEFAULT_PAGE_SIZE in options else options[-1]


def merged_user_defined_fields(stored):
    merged = default_user_defined_fields()
    for key, config in (stored or {}).items():
        if key in merged:
            label = (config.get('label') or '').strip()
            merged[key] = {'label': label or merged[key]['label'], 'description': config.get('description') or ''}
    return merged


def merged_media_quality(stored):
    merged = default_media_quality()
    for metric, config in (stored or {}).items():
        if metric in merged:
            merged[metric].update({name: config.get(name, merged[metric][name]) for name in ('warning', 'critical', 'unit')})
    for metric, config in merged.items():
        config['field'] = MEDIA_QUALITY_METRICS[metric]
        # Status colouring applies only with a unit and at least one threshold; units are never assumed.
        config['configured'] = bool((config['unit'] or '').strip()) and (config['warning'] is not None or config['critical'] is not None)
    return merged


def serialize_profile(profile):
    if profile is None:
        return None
    return {
        'host': profile.host,
        'port': profile.port,
        'database_name': profile.database_name,
        'username': profile.username,
        'has_password': bool(profile.password_encrypted),
        'sslmode': profile.sslmode,
        'sslrootcert': profile.sslrootcert,
        'connect_timeout': profile.connect_timeout,
        'is_enabled': profile.is_enabled,
        'updated_at': profile.updated_at,
    }


def serialize_settings(module_settings):
    profiles = {profile.role: profile for profile in CdrSourceProfile.objects.all()}
    return {
        'active_source': module_settings.active_source,
        'profiles': {role: serialize_profile(profiles.get(role)) for role in SourceRole.values},
        **{field: getattr(module_settings, field) for field in SCALAR_FIELDS if field != 'active_source'},
        'user_defined_fields': merged_user_defined_fields(module_settings.user_defined_fields),
        'media_quality': merged_media_quality(module_settings.media_quality),
        'field_help_overrides': module_settings.field_help_overrides or {},
        'encryption_key_status': key_status(),
        'config_version': module_settings.config_version,
        'updated_at': module_settings.updated_at,
        'updated_by': module_settings.updated_by_text,
    }


def _apply_profile(role, data):
    """Create, update or delete one profile. Returns the names (never values) of what changed."""
    existing = CdrSourceProfile.objects.filter(role=role).first()
    if data is None:
        if existing is None:
            return []
        existing.delete()
        return ['deleted']

    password = data.get('password')
    if existing is None and not password:
        raise ValidationError({'profiles': {role: {'password': ['A password is required for a new source profile.']}}})

    profile = existing or CdrSourceProfile(role=role)
    changed = [] if existing else ['created']
    for field in PROFILE_FIELDS:
        if field in data and getattr(profile, field) != data[field]:
            setattr(profile, field, data[field])
            if existing:
                changed.append(field)
    if password:
        profile.password_encrypted = encrypt_secret(password)
        changed.append('password')
    if changed:
        profile.save()
    return changed


@transaction.atomic
def update_settings(user, data):
    CdrModuleSettings.load()
    module_settings = CdrModuleSettings.objects.select_for_update().get(pk=CdrModuleSettings.SINGLETON_ID)

    changes = {}
    for field in SCALAR_FIELDS:
        if field in data and getattr(module_settings, field) != data[field]:
            changes[field] = {'from': getattr(module_settings, field), 'to': data[field]}
            setattr(module_settings, field, data[field])

    json_changed = []
    for field in JSON_FIELDS:
        if field in data and getattr(module_settings, field) != data[field]:
            json_changed.append(field)
            setattr(module_settings, field, data[field])

    profile_changes = {}
    for role, profile_data in (data.get('profiles') or {}).items():
        changed = _apply_profile(role, profile_data)
        if changed:
            profile_changes[role] = changed

    if not (changes or json_changed or profile_changes):
        return module_settings

    module_settings.config_version += 1
    module_settings.updated_by_text = user.email
    module_settings.save()

    AuditService.record_event(
        event_type='cdr.settings.updated',
        result='success',
        actor=user,
        object_type='cdr_settings',
        object_id_text=str(module_settings.pk),
        object_name='AudioCodes CDR settings',
        message='AudioCodes CDR module settings updated.',
        metadata={
            'changes': changes,
            'json_fields_changed': json_changed,
            'profile_changes': profile_changes,
            'config_version': module_settings.config_version,
        },
    )
    return module_settings


def get_duration_format(user):
    preference = CdrUserPreference.objects.filter(user=user).first()
    return preference.duration_format if preference else DurationFormat.HMS


def set_duration_format(user, duration_format):
    CdrUserPreference.objects.update_or_create(user=user, defaults={'duration_format': duration_format})
    return duration_format


def build_display_config(module_settings, user):
    return {
        'timezone': 'Australia/Sydney',
        'max_range_months': MAX_RANGE_MONTHS,
        'active_source': module_settings.active_source,
        'source_credential_usable': key_status() == KEY_OK,
        'duration_format': get_duration_format(user),
        'duration_unit': 'hundredths_of_second',
        'page_size_options': page_size_options(module_settings),
        'default_page_size': default_page_size(module_settings),
        'max_page_size': module_settings.max_page_size,
        'max_multiselect_values': module_settings.max_multiselect_values,
        'hourly_bucket_max_hours': module_settings.hourly_bucket_max_hours,
        'presets': list(PRESETS),
        'match_modes': list(MATCH_MODES),
        'status_options': list(STATUS_FILTERS),
        'sort_fields': list(SORT_FIELDS),
        'user_defined_fields': merged_user_defined_fields(module_settings.user_defined_fields),
        'media_quality': merged_media_quality(module_settings.media_quality),
        'help': build_field_help(module_settings.field_help_overrides),
    }
