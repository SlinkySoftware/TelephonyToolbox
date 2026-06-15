# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from audit.views import AuditExportCsvView, AuditListView


urlpatterns = [
    path('admin/audit/', AuditListView.as_view(), name='admin-audit'),
    path('admin/audit/export.csv', AuditExportCsvView.as_view(), name='admin-audit-export'),
]