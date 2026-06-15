# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from audit.models import AuditEvent


class AuditService:
    @staticmethod
    def record_event(
        *,
        event_type,
        result,
        actor=None,
        actor_email='',
        object_type='',
        object_id_text='',
        object_name='',
        source_number='',
        destination_number='',
        message='',
        metadata=None,
    ):
        if actor is not None and getattr(actor, 'is_authenticated', False):
            actor_user_id_text = str(actor.pk)
            actor_email = actor.email
            actor_display_name = actor.display_name
            actor_auth_source = actor.auth_source
        else:
            actor_user_id_text = ''
            actor_display_name = ''
            actor_auth_source = ''

        return AuditEvent.objects.create(
            event_type=event_type,
            result=result,
            actor_user_id_text=actor_user_id_text,
            actor_email=actor_email,
            actor_display_name=actor_display_name,
            actor_auth_source=actor_auth_source,
            object_type=object_type,
            object_id_text=object_id_text,
            object_name=object_name,
            source_number=source_number,
            destination_number=destination_number,
            message=message,
            metadata_json=metadata or {},
        )