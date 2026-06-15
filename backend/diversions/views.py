# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access_groups.models import AccessGroup
from accounts.permissions import IsAppAdmin
from audit.services import AuditService
from cucm.exceptions import CucmAuthenticationError, CucmUnavailableError
from diversions.models import Diversion
from diversions.permissions import visible_diversions_queryset
from diversions.serializers import (
    AdminDiversionCreateSerializer,
    AdminDiversionUpdateSerializer,
    DestinationInputSerializer,
    DiversionSerializer,
    SourceValidationInputSerializer,
)
from diversions.services import DiversionAdminService, DiversionUpdateService, cucm_status_value, validation_response


class VisibleDiversionListView(APIView):
    def get(self, request):
        queryset = visible_diversions_queryset(request.user)
        status_value = cucm_status_value()
        data = DiversionSerializer(queryset, many=True).data
        for item in data:
            item['cucm_status'] = status_value
        return Response({'results': data})


class VisibleDiversionDetailView(APIView):
    def get(self, request, diversion_id):
        diversion = get_object_or_404(visible_diversions_queryset(request.user), pk=diversion_id)
        data = DiversionSerializer(diversion).data
        data['cucm_status'] = cucm_status_value()
        return Response(data)


class ValidateDestinationView(APIView):
    def post(self, request, diversion_id):
        get_object_or_404(visible_diversions_queryset(request.user), pk=diversion_id)
        serializer = DestinationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = validation_response(serializer.validated_data['destination'])
        return Response(payload, status=status.HTTP_200_OK if payload['is_valid'] else status.HTTP_400_BAD_REQUEST)


class UpdateDestinationView(APIView):
    def post(self, request, diversion_id):
        diversion = get_object_or_404(visible_diversions_queryset(request.user), pk=diversion_id)
        serializer = DestinationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_code, payload = DiversionUpdateService.update_destination(request.user, diversion, serializer.validated_data['destination'])
        if status_code == 200:
            refreshed = Diversion.objects.select_related('group').get(pk=diversion.pk)
            payload['diversion'] = DiversionSerializer(refreshed).data
            payload['diversion']['cucm_status'] = 'available'
        return Response(payload, status=status_code)


class RefreshDiversionView(APIView):
    def post(self, request, diversion_id):
        diversion = get_object_or_404(visible_diversions_queryset(request.user), pk=diversion_id)
        status_code, payload = DiversionUpdateService.refresh_diversion(request.user, diversion)
        if status_code == 200:
            refreshed = Diversion.objects.select_related('group').get(pk=diversion.pk)
            payload['diversion'] = DiversionSerializer(refreshed).data
            payload['diversion']['cucm_status'] = 'available'
        return Response(payload, status=status_code)


class AdminDiversionListCreateView(APIView):
    permission_classes = [IsAppAdmin]

    def get(self, request):
        queryset = Diversion.objects.select_related('group').order_by('name')
        data = DiversionSerializer(queryset, many=True).data
        status_value = cucm_status_value()
        for item in data:
            item['cucm_status'] = status_value
        return Response({'results': data})

    def post(self, request):
        serializer = AdminDiversionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            validation = DiversionAdminService.validate_source_number(payload['source_number'])
        except (CucmUnavailableError, CucmAuthenticationError):
            return Response({'message': 'CUCM is currently unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if not validation['exists_in_cucm']:
            return Response({'message': 'Source number was not found in CUCM.'}, status=status.HTTP_400_BAD_REQUEST)
        if validation['already_exists_in_app']:
            return Response({'message': 'This source number already exists in Telephony Toolbox.'}, status=status.HTTP_400_BAD_REQUEST)

        group = get_object_or_404(AccessGroup, pk=payload['group_id'])
        diversion = Diversion.objects.create(
            name=payload['name'],
            description=payload.get('description', ''),
            source_number=payload['source_number'],
            source_partition=settings.CUCM_ROUTE_PARTITION,
            cached_current_destination=validation['current_destination'] or '',
            group=group,
            last_refreshed_at=None,
            created_by_text=request.user.email,
        )
        AuditService.record_event(
            event_type='diversion.created',
            result='success',
            actor=request.user,
            object_type='diversion',
            object_id_text=str(diversion.pk),
            object_name=diversion.name,
            source_number=diversion.source_number,
            destination_number=diversion.cached_current_destination,
            message='Diversion created successfully.',
        )
        return Response(DiversionSerializer(diversion).data, status=status.HTTP_201_CREATED)


class AdminDiversionValidateSourceView(APIView):
    permission_classes = [IsAppAdmin]

    def post(self, request):
        serializer = SourceValidationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            result = DiversionAdminService.validate_source_number(payload['source_number'])
        except (CucmUnavailableError, CucmAuthenticationError):
            return Response({'message': 'CUCM is currently unavailable.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        AuditService.record_event(
            event_type='diversion.source_validation.success' if result['exists_in_cucm'] else 'diversion.source_validation.failure',
            result='success' if result['exists_in_cucm'] else 'failure',
            actor=request.user,
            object_type='diversion',
            object_name=payload['source_number'],
            source_number=payload['source_number'],
            destination_number=result.get('current_destination', ''),
            message='Source number validation completed.',
            metadata=result,
        )
        return Response(result)


class AdminDiversionDetailView(APIView):
    permission_classes = [IsAppAdmin]

    def get_object(self, diversion_id):
        return get_object_or_404(Diversion.objects.select_related('group'), pk=diversion_id)

    def get(self, request, diversion_id):
        diversion = self.get_object(diversion_id)
        data = DiversionSerializer(diversion).data
        data['cucm_status'] = cucm_status_value()
        return Response(data)

    def patch(self, request, diversion_id):
        diversion = self.get_object(diversion_id)
        serializer = AdminDiversionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if 'name' in payload:
            diversion.name = payload['name']
        if 'description' in payload:
            diversion.description = payload['description']
        if 'group_id' in payload:
            diversion.group = get_object_or_404(AccessGroup, pk=payload['group_id'])
        diversion.save()

        AuditService.record_event(
            event_type='diversion.updated_metadata',
            result='success',
            actor=request.user,
            object_type='diversion',
            object_id_text=str(diversion.pk),
            object_name=diversion.name,
            source_number=diversion.source_number,
            message='Diversion metadata updated successfully.',
        )
        return Response(DiversionSerializer(diversion).data)

    def delete(self, request, diversion_id):
        diversion = self.get_object(diversion_id)
        AuditService.record_event(
            event_type='diversion.deleted',
            result='success',
            actor=request.user,
            object_type='diversion',
            object_id_text=str(diversion.pk),
            object_name=diversion.name,
            source_number=diversion.source_number,
            message='Diversion deleted from Telephony Toolbox only. CUCM was not changed.',
        )
        diversion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)