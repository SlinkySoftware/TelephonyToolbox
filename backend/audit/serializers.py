from rest_framework import serializers

from audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
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