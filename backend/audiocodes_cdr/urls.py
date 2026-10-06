# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from audiocodes_cdr.views import (
    DisplayConfigView,
    EgressIpGroupLookupView,
    IngressIpGroupLookupView,
    ModuleSettingsView,
    PreferencesView,
    SdrDetailView,
    SdrListView,
    StatisticsIpGroupsView,
    StatisticsSummaryView,
    StatisticsTerminationReasonsView,
    StatisticsTimeseriesView,
    TerminationReasonLookupView,
)


urlpatterns = [
    path('admin/cdr/sdr/', SdrListView.as_view(), name='cdr-sdr-list'),
    path('admin/cdr/sdr/<int:sdr_id>/', SdrDetailView.as_view(), name='cdr-sdr-detail'),
    path('admin/cdr/lookups/ingress-ip-groups/', IngressIpGroupLookupView.as_view(), name='cdr-lookup-ingress-ip-groups'),
    path('admin/cdr/lookups/egress-ip-groups/', EgressIpGroupLookupView.as_view(), name='cdr-lookup-egress-ip-groups'),
    path('admin/cdr/lookups/termination-reasons/', TerminationReasonLookupView.as_view(), name='cdr-lookup-termination-reasons'),
    path('admin/cdr/statistics/summary/', StatisticsSummaryView.as_view(), name='cdr-statistics-summary'),
    path('admin/cdr/statistics/timeseries/', StatisticsTimeseriesView.as_view(), name='cdr-statistics-timeseries'),
    path('admin/cdr/statistics/ip-groups/', StatisticsIpGroupsView.as_view(), name='cdr-statistics-ip-groups'),
    path('admin/cdr/statistics/termination-reasons/', StatisticsTerminationReasonsView.as_view(), name='cdr-statistics-termination-reasons'),
    path('admin/cdr/config/display/', DisplayConfigView.as_view(), name='cdr-display-config'),
    path('admin/cdr/preferences/', PreferencesView.as_view(), name='cdr-preferences'),
    path('admin/cdr/settings/', ModuleSettingsView.as_view(), name='cdr-settings'),
]
