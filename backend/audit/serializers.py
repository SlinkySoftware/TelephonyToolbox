# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from rest_framework import serializers

from audit.models import AuditEvent
from cucm.directory_numbers import normalise_directory_number_pattern


class AuditEventSerializer(serializers.ModelSerializer):
    source_number = serializers.SerializerMethodField()

    def get_source_number(self, obj):
        return normalise_directory_number_pattern(obj.source_number)

    class Meta:
        model = AuditEvent
        fields = (
            'id',
            'timestamp',
            'event_type',
            'result',
            'actor_user_id_text',
            'actor_email',
            'actor_display_name',
            'actor_auth_source',
            'object_type',
            'object_id_text',
            'object_name',
            'source_number',
            'destination_number',
            'message',
            'metadata_json',
        )