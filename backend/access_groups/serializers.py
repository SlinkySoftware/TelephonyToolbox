# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from rest_framework import serializers

from access_groups.models import AccessGroup


class AccessGroupSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)
    diversion_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AccessGroup
        fields = ('id', 'name', 'description', 'user_count', 'diversion_count', 'created_at', 'updated_at')