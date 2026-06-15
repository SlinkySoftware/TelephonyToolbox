# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.contrib.auth import get_user_model
from rest_framework import serializers

from access_groups.models import AccessGroup, UserGroupMembership
from accounts.models import AuthSource, UserRole


User = get_user_model()
REQUIRED_FIELD_MESSAGE = 'This field is required.'


class GroupSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGroup
        fields = ('id', 'name')


class CurrentUserSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'display_name', 'role', 'auth_source', 'groups', 'permissions')

    def get_groups(self, obj):
        groups = AccessGroup.objects.filter(user_memberships__user=obj).order_by('name').distinct()
        return GroupSummarySerializer(groups, many=True).data

    def get_permissions(self, obj):
        return {'is_app_admin': obj.role == UserRole.APP_ADMIN}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class ExternalValidationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AdminUserReadSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'display_name', 'role', 'auth_source', 'is_active', 'is_local', 'groups', 'created_at', 'updated_at')

    def get_groups(self, obj):
        groups = AccessGroup.objects.filter(user_memberships__user=obj).order_by('name').distinct()
        return GroupSummarySerializer(groups, many=True).data


class AdminUserWriteSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    display_name = serializers.CharField(max_length=255, required=False)
    auth_source = serializers.ChoiceField(choices=AuthSource.choices, required=False)
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    group_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    password = serializers.CharField(required=False, trim_whitespace=False, allow_blank=False)

    def validate(self, attrs):
        auth_source = attrs.get('auth_source', getattr(self.instance, 'auth_source', None))
        password = attrs.get('password')
        if self.instance is None and not attrs.get('email'):
            raise serializers.ValidationError({'email': REQUIRED_FIELD_MESSAGE})
        if self.instance is None and not attrs.get('display_name'):
            raise serializers.ValidationError({'display_name': REQUIRED_FIELD_MESSAGE})
        if self.instance is None and not attrs.get('role'):
            raise serializers.ValidationError({'role': REQUIRED_FIELD_MESSAGE})
        if self.instance is None and not auth_source:
            raise serializers.ValidationError({'auth_source': REQUIRED_FIELD_MESSAGE})

        if auth_source == AuthSource.LOCAL and self.instance is None and not password:
            raise serializers.ValidationError({'password': 'A password is required for local users.'})
        if auth_source != AuthSource.LOCAL and password:
            raise serializers.ValidationError({'password': 'Passwords are only permitted for local users.'})
        return attrs


def sync_memberships(user, group_ids):
    group_ids = list(group_ids or [])
    UserGroupMembership.objects.filter(user=user).exclude(group_id__in=group_ids).delete()
    existing = set(UserGroupMembership.objects.filter(user=user, group_id__in=group_ids).values_list('group_id', flat=True))
    memberships = [UserGroupMembership(user=user, group_id=group_id) for group_id in group_ids if group_id not in existing]
    if memberships:
        UserGroupMembership.objects.bulk_create(memberships)