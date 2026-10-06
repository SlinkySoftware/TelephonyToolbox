# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.http import QueryDict
from django.utils.cache import patch_cache_control
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAppAdmin
from audiocodes_cdr import detail, lookups, search, statistics
from audiocodes_cdr.exceptions import InvalidFilters
from audiocodes_cdr.models import CdrModuleSettings
from audiocodes_cdr.serializers import (
    ModuleSettingsUpdateSerializer,
    PreferencesSerializer,
    SdrSearchSerializer,
    StatisticsFilterSerializer,
)
from audiocodes_cdr.settings_service import (
    build_display_config,
    get_duration_format,
    serialize_settings,
    set_duration_format,
    update_settings,
)


def normalised_query_params(request):
    """Accept both ``key=a&key=b`` and ``key[]=a&key[]=b`` for multi-value filters."""
    params = QueryDict(mutable=True)
    for key, values in request.query_params.lists():
        name = key[:-2] if key.endswith('[]') else key
        params.setlist(name, params.getlist(name) + values)
    return params


class CdrAdminView(APIView):
    """Base view: App Admin only, never cached by browsers or shared intermediaries."""

    permission_classes = [IsAppAdmin]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True, private=True)
        return response

    def validated_filters(self, serializer_class, module_settings):
        serializer = serializer_class(data=normalised_query_params(self.request), context={'module_settings': module_settings})
        if not serializer.is_valid():
            raise InvalidFilters(serializer.errors)
        return serializer.validated_data


class SdrListView(CdrAdminView):
    def get(self, request):
        module_settings = CdrModuleSettings.load()
        filters = self.validated_filters(SdrSearchSerializer, module_settings)
        return Response(search.search_sdrs(filters, module_settings))


class SdrDetailView(CdrAdminView):
    def get(self, request, sdr_id):
        return Response(detail.get_session_detail(sdr_id, CdrModuleSettings.load()))


class IngressIpGroupLookupView(CdrAdminView):
    def get(self, request):
        return Response(lookups.ingress_ip_groups(CdrModuleSettings.load()))


class EgressIpGroupLookupView(CdrAdminView):
    def get(self, request):
        return Response(lookups.egress_ip_groups(CdrModuleSettings.load()))


class TerminationReasonLookupView(CdrAdminView):
    def get(self, request):
        return Response(lookups.termination_reasons(CdrModuleSettings.load()))


class StatisticsView(CdrAdminView):
    compute = None

    def get(self, request):
        module_settings = CdrModuleSettings.load()
        filters = self.validated_filters(StatisticsFilterSerializer, module_settings)
        return Response(self.compute(filters, module_settings))


class StatisticsSummaryView(StatisticsView):
    compute = staticmethod(statistics.summary)


class StatisticsTimeseriesView(StatisticsView):
    compute = staticmethod(statistics.timeseries)


class StatisticsIpGroupsView(StatisticsView):
    compute = staticmethod(statistics.ip_groups)


class StatisticsTerminationReasonsView(StatisticsView):
    compute = staticmethod(statistics.termination_reasons)


class DisplayConfigView(CdrAdminView):
    def get(self, request):
        return Response(build_display_config(CdrModuleSettings.load(), request.user))


class PreferencesView(CdrAdminView):
    def get(self, request):
        return Response({'duration_format': get_duration_format(request.user)})

    def put(self, request):
        serializer = PreferencesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'duration_format': set_duration_format(request.user, serializer.validated_data['duration_format'])})


class ModuleSettingsView(CdrAdminView):
    def get(self, request):
        return Response(serialize_settings(CdrModuleSettings.load()))

    def put(self, request):
        serializer = ModuleSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serialize_settings(update_settings(request.user, serializer.validated_data)))
