from rest_framework import serializers

from accounts.serializers import GroupSummarySerializer
from diversions.models import Diversion


class DiversionSerializer(serializers.ModelSerializer):
    group = GroupSummarySerializer(read_only=True)
    last_updated_by = serializers.CharField(source='last_updated_by_text', read_only=True)
    cucm_status = serializers.CharField(read_only=True)

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


class AdminDiversionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    source_number = serializers.CharField(max_length=64)
    group_id = serializers.UUIDField()


class AdminDiversionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    group_id = serializers.UUIDField(required=False)