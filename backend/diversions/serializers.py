# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from rest_framework import serializers

from accounts.serializers import GroupSummarySerializer
from cucm.directory_numbers import normalise_directory_number_pattern
from diversions.models import Diversion


class DiversionSerializer(serializers.ModelSerializer):
    group = GroupSummarySerializer(read_only=True)
    source_number = serializers.SerializerMethodField()
    last_updated_by = serializers.CharField(source='last_updated_by_text', read_only=True)
    cucm_status = serializers.CharField(read_only=True)

    def get_source_number(self, obj):
        return normalise_directory_number_pattern(obj.source_number)

    class Meta:
        model = Diversion
        fields = (
            'id',
            'name',
            'description',
            'source_number',
            'cached_current_destination',
            'group',
            'last_refreshed_at',
            'last_updated_at',
            'last_updated_by',
            'cucm_status',
        )


class DestinationInputSerializer(serializers.Serializer):
    destination = serializers.CharField()


class SourceValidationInputSerializer(serializers.Serializer):
    source_number = serializers.CharField(max_length=64)

    def validate_source_number(self, value):
        return normalise_directory_number_pattern(value)


class AdminDiversionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    source_number = serializers.CharField(max_length=64)
    group_id = serializers.UUIDField()

    def validate_source_number(self, value):
        return normalise_directory_number_pattern(value)


class AdminDiversionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    group_id = serializers.UUIDField(required=False)