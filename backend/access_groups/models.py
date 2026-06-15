# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.conf import settings
from django.db import models

from telephony_toolbox.models import UUIDModel, UUIDTimestampedModel


class AccessGroup(UUIDTimestampedModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class UserGroupMembership(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(AccessGroup, on_delete=models.CASCADE, related_name='user_memberships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'group'), name='unique_user_group_membership'),
        ]
        ordering = ('group__name', 'user__email')

    def __str__(self):
        return f'{self.user.email} -> {self.group.name}'