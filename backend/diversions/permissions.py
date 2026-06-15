# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from accounts.models import UserRole
from diversions.models import Diversion


def visible_diversions_queryset(user):
    queryset = Diversion.objects.select_related('group').order_by('name')
    if user.role == UserRole.APP_ADMIN:
        return queryset
    return queryset.filter(group__user_memberships__user=user).distinct()


def user_can_access_diversion(user, diversion):
    if user.role == UserRole.APP_ADMIN:
        return True
    return diversion.group.user_memberships.filter(user=user).exists()