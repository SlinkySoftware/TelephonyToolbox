# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import re

from rest_framework import serializers

from audiocodes_cdr.constants import HARD_MAX_PAGE_SIZE, MATCH_MODES, STATUS_FILTERS
from audiocodes_cdr.field_help import is_valid_override_key
from audiocodes_cdr.models import DurationFormat, SourceRole, SslMode
from audiocodes_cdr.search import SORT_FIELDS
from audiocodes_cdr.settings_service import default_page_size, page_size_options
from audiocodes_cdr.timeutils import PRESETS, NonexistentLocalTime, parse_datetime_value, range_exceeds_limit, resolve_preset, to_sydney_iso

HOST_PATTERN = re.compile(r'^[A-Za-z0-9.\-:\[\]%]+$')
IDENTIFIER_PATTERN = re.compile(r'^[^\s\x00-\x1f\x7f]+$')
MAX_FILTER_TEXT = 255


class SydneyDateTimeField(serializers.Field):
    """ISO 8601 date/time. Values without an offset are Australia/Sydney local time."""

    default_error_messages = {
        'invalid': 'Enter a valid ISO 8601 date and time.',
        'nonexistent': 'This local time does not exist in Australia/Sydney (daylight-saving change). Include a UTC offset.',
    }

    def to_internal_value(self, data):
        if not isinstance(data, str) or not data.strip() or len(data) > 64:
            self.fail('invalid')
        try:
            return parse_datetime_value(data)
        except NonexistentLocalTime:
            self.fail('nonexistent')
        except (ValueError, OverflowError):
            self.fail('invalid')

    def to_representation(self, value):
        return to_sydney_iso(value)


def _text_filter(**kwargs):
    return serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_FILTER_TEXT, **kwargs)


def _multi_filter():
    return serializers.ListField(
        child=serializers.CharField(max_length=MAX_FILTER_TEXT, allow_blank=True, trim_whitespace=False),
        required=False,
        default=list,
    )


class RangeSerializer(serializers.Serializer):
    start = SydneyDateTimeField(required=False)
    end = SydneyDateTimeField(required=False)
    preset = serializers.ChoiceField(choices=PRESETS, required=False)

    def validate(self, attrs):
        if attrs.get('preset'):
            attrs['start'], attrs['end'] = resolve_preset(attrs['preset'])
        else:
            missing = {name: ['This field is required.'] for name in ('start', 'end') if attrs.get(name) is None}
            if missing:
                raise serializers.ValidationError(missing, code='required')
        if attrs['start'] >= attrs['end']:
            raise serializers.ValidationError({'end': ['The end time must be after the start time.']}, code='invalid_range')
        if range_exceeds_limit(attrs['start'], attrs['end']):
            raise serializers.ValidationError({'end': ['The range cannot exceed 12 months.']}, code='range_too_large')
        return attrs


class SdrFilterSerializer(RangeSerializer):
    ingress_ip_group = _multi_filter()
    egress_ip_group = _multi_filter()
    ani = _text_filter()
    ani_match = serializers.ChoiceField(choices=MATCH_MODES, default='contains')
    dnis = _text_filter()
    dnis_match = serializers.ChoiceField(choices=MATCH_MODES, default='contains')
    call_id = _text_filter()
    call_id_match = serializers.ChoiceField(choices=MATCH_MODES, default='exact')
    status = serializers.ChoiceField(choices=STATUS_FILTERS, default='all')
    termination_reason = _multi_filter()
    termination_text = _text_filter()
    termination_match = serializers.ChoiceField(choices=MATCH_MODES, default='contains')

    def _validate_multi(self, values):
        values = list(dict.fromkeys(value for value in values if value.strip()))
        limit = self.context['module_settings'].max_multiselect_values
        if len(values) > limit:
            raise serializers.ValidationError(f'Select no more than {limit} values.')
        return values

    def validate_ingress_ip_group(self, values):
        return self._validate_multi(values)

    def validate_egress_ip_group(self, values):
        return self._validate_multi(values)

    def validate_termination_reason(self, values):
        return self._validate_multi(values)


class SdrSearchSerializer(SdrFilterSerializer):
    sort = serializers.ChoiceField(choices=SORT_FIELDS, default='setuptime')
    direction = serializers.ChoiceField(choices=('asc', 'desc'), default='desc')
    page = serializers.IntegerField(min_value=1, max_value=1_000_000, default=1)
    page_size = serializers.IntegerField(required=False)

    def validate_page_size(self, value):
        options = page_size_options(self.context['module_settings'])
        if value not in options:
            raise serializers.ValidationError(f'Choose one of: {", ".join(str(option) for option in options)}.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs.setdefault('page_size', default_page_size(self.context['module_settings']))
        return attrs


class StatisticsFilterSerializer(SdrFilterSerializer):
    pass


class PreferencesSerializer(serializers.Serializer):
    duration_format = serializers.ChoiceField(choices=DurationFormat.choices)


class SourceProfileSerializer(serializers.Serializer):
    host = serializers.CharField(max_length=255)
    port = serializers.IntegerField(min_value=1, max_value=65535, default=5432)
    database_name = serializers.CharField(max_length=63)
    username = serializers.CharField(max_length=63)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=1024,
        trim_whitespace=False,
    )
    sslmode = serializers.ChoiceField(choices=SslMode.choices, default=SslMode.PREFER)
    sslrootcert = serializers.CharField(max_length=1024, required=False, allow_blank=True, default='')
    connect_timeout = serializers.IntegerField(min_value=1, max_value=60, default=10)
    is_enabled = serializers.BooleanField(default=True)

    def validate_host(self, value):
        if not HOST_PATTERN.match(value):
            raise serializers.ValidationError('Enter a valid host name or IP address.')
        return value

    def validate_database_name(self, value):
        if not IDENTIFIER_PATTERN.match(value):
            raise serializers.ValidationError('Database name must not contain spaces or control characters.')
        return value

    def validate_username(self, value):
        if not IDENTIFIER_PATTERN.match(value):
            raise serializers.ValidationError('Username must not contain spaces or control characters.')
        return value

    def validate_sslrootcert(self, value):
        if value and value != 'system' and not value.startswith('/'):
            raise serializers.ValidationError('Use an absolute path, "system", or leave blank.')
        return value


class SourceProfilesSerializer(serializers.Serializer):
    replica = SourceProfileSerializer(required=False, allow_null=True)
    primary = SourceProfileSerializer(required=False, allow_null=True)


class UserDefinedFieldSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class MediaThresholdSerializer(serializers.Serializer):
    warning = serializers.FloatField(required=False, allow_null=True, default=None, min_value=0)
    critical = serializers.FloatField(required=False, allow_null=True, default=None, min_value=0)
    unit = serializers.CharField(max_length=32, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        warning, critical = attrs['warning'], attrs['critical']
        if (warning is not None or critical is not None) and not attrs['unit'].strip():
            raise serializers.ValidationError({'unit': ['A unit is required when a threshold is set.']})
        if warning is not None and critical is not None and critical < warning:
            raise serializers.ValidationError({'critical': ['The critical threshold must be greater than or equal to the warning threshold.']})
        return attrs


class UserDefinedFieldsSerializer(serializers.Serializer):
    varcalluserdefined1 = UserDefinedFieldSerializer(required=False)
    varcalluserdefined2 = UserDefinedFieldSerializer(required=False)
    varcalluserdefined3 = UserDefinedFieldSerializer(required=False)
    varcalluserdefined4 = UserDefinedFieldSerializer(required=False)
    varcalluserdefined5 = UserDefinedFieldSerializer(required=False)


class MediaQualitySerializer(serializers.Serializer):
    local_jitter = MediaThresholdSerializer(required=False)
    remote_jitter = MediaThresholdSerializer(required=False)
    local_packet_loss = MediaThresholdSerializer(required=False)
    remote_packet_loss = MediaThresholdSerializer(required=False)
    local_round_trip_delay = MediaThresholdSerializer(required=False)
    remote_round_trip_delay = MediaThresholdSerializer(required=False)


class ModuleSettingsUpdateSerializer(serializers.Serializer):
    active_source = serializers.ChoiceField(choices=SourceRole.choices, required=False)
    profiles = SourceProfilesSerializer(required=False)
    max_page_size = serializers.IntegerField(min_value=25, max_value=HARD_MAX_PAGE_SIZE, required=False)
    max_multiselect_values = serializers.IntegerField(min_value=1, max_value=200, required=False)
    lookup_cache_seconds = serializers.IntegerField(min_value=0, max_value=86400, required=False)
    statistics_cache_seconds = serializers.IntegerField(min_value=0, max_value=86400, required=False)
    termination_lookup_days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    hourly_bucket_max_hours = serializers.IntegerField(min_value=24, max_value=744, required=False)
    user_defined_fields = UserDefinedFieldsSerializer(required=False)
    media_quality = MediaQualitySerializer(required=False)
    field_help_overrides = serializers.DictField(
        child=serializers.CharField(max_length=2000, allow_blank=False),
        required=False,
    )

    def validate_field_help_overrides(self, value):
        if len(value) > 500:
            raise serializers.ValidationError('Too many help overrides.')
        invalid = sorted(key for key in value if not is_valid_override_key(key))
        if invalid:
            raise serializers.ValidationError(f'Unknown help keys: {", ".join(invalid[:10])}.')
        return value
