# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from health.views import AdminHealthView, HealthCheckView, HealthzView


urlpatterns = [
    path('healthz', HealthzView.as_view(), name='healthz'),
    path('healthcheck', HealthCheckView.as_view(), name='healthcheck'),
    path('admin/health/', AdminHealthView.as_view(), name='admin-health'),
]