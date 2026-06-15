# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access_groups.models import AccessGroup
from access_groups.serializers import AccessGroupSerializer
from accounts.permissions import IsAppAdmin
from audit.services import AuditService


class AdminGroupListCreateView(APIView):
    permission_classes = [IsAppAdmin]

    def _queryset(self):
        return AccessGroup.objects.annotate(
            user_count=Count('user_memberships', distinct=True),
            diversion_count=Count('diversions', distinct=True),
        ).order_by('name')

    def get(self, request):
        queryset = self._queryset()
        search_term = request.query_params.get('search', '').strip()
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)
        return Response(AccessGroupSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = AccessGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        AuditService.record_event(
            event_type='group.created',
            result='success',
            actor=request.user,
            object_type='group',
            object_id_text=str(group.pk),
            object_name=group.name,
            message='Group created successfully.',
        )
        return Response(AccessGroupSerializer(self._queryset().get(pk=group.pk)).data, status=status.HTTP_201_CREATED)


class AdminGroupDetailView(APIView):
    permission_classes = [IsAppAdmin]

    def _queryset(self):
        return AccessGroup.objects.annotate(
            user_count=Count('user_memberships', distinct=True),
            diversion_count=Count('diversions', distinct=True),
        )

    def get_object(self, group_id):
        return get_object_or_404(self._queryset(), pk=group_id)

    def get(self, request, group_id):
        return Response(AccessGroupSerializer(self.get_object(group_id)).data)

    def patch(self, request, group_id):
        group = AccessGroup.objects.get(pk=group_id)
        serializer = AccessGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        AuditService.record_event(
            event_type='group.updated',
            result='success',
            actor=request.user,
            object_type='group',
            object_id_text=str(group.pk),
            object_name=group.name,
            message='Group updated successfully.',
        )
        return Response(AccessGroupSerializer(self.get_object(group_id)).data)

    def delete(self, request, group_id):
        group = AccessGroup.objects.get(pk=group_id)
        if group.diversions.exists():
            AuditService.record_event(
                event_type='group.delete_blocked',
                result='failure',
                actor=request.user,
                object_type='group',
                object_id_text=str(group.pk),
                object_name=group.name,
                message='Group deletion blocked because diversions are assigned.',
            )
            return Response(
                {
                    'result': 'failure',
                    'error_code': 'group_contains_diversions',
                    'message': 'This group cannot be deleted because it contains diversions.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        AuditService.record_event(
            event_type='group.deleted',
            result='success',
            actor=request.user,
            object_type='group',
            object_id_text=str(group.pk),
            object_name=group.name,
            message='Group deleted successfully.',
        )
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)