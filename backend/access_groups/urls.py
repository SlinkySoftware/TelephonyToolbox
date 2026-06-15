# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from access_groups.views import AdminGroupDetailView, AdminGroupListCreateView


urlpatterns = [
    path('admin/groups/', AdminGroupListCreateView.as_view(), name='admin-groups'),
    path('admin/groups/<uuid:group_id>/', AdminGroupDetailView.as_view(), name='admin-group-detail'),
]