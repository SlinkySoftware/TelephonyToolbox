# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from audit.models import AuditEvent
from audit.services import AuditService


@pytest.mark.django_db
def test_audit_event_remains_readable_after_user_deletion(admin_user):
    event = AuditService.record_event(
        event_type='user.deleted',
        result='success',
        actor=admin_user,
        object_type='user',
        object_name=admin_user.email,
        message='User deleted successfully.',
    )

    admin_user.delete()

    persisted = AuditEvent.objects.get(pk=event.pk)
    assert persisted.actor_email == 'admin@example.com'
    assert persisted.actor_display_name == 'Admin User'