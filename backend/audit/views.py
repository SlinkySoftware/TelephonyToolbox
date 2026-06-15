import csv
import json

from django.http import HttpResponse
from rest_framework.generics import ListAPIView

from accounts.permissions import IsAppAdmin
from audit.models import AuditEvent
from audit.serializers import AuditEventSerializer


class AuditQueryMixin:
    permission_classes = [IsAppAdmin]

    def get_queryset(self):
        queryset = AuditEvent.objects.all().order_by('-timestamp')
        params = self.request.query_params

        start_date = params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        end_date = params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        actor_email = params.get('actor_email')
        if actor_email:
            queryset = queryset.filter(actor_email__icontains=actor_email)
        event_type = params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        result = params.get('result')
        if result:
            queryset = queryset.filter(result=result)
        object_type = params.get('object_type')
        if object_type:
            queryset = queryset.filter(object_type=object_type)
        source_number = params.get('source_number')
        if source_number:
            queryset = queryset.filter(source_number__icontains=source_number)
        destination_number = params.get('destination_number')
        if destination_number:
            queryset = queryset.filter(destination_number__icontains=destination_number)
        return queryset


class AuditListView(AuditQueryMixin, ListAPIView):
    serializer_class = AuditEventSerializer


class AuditExportCsvView(AuditQueryMixin, ListAPIView):
    pagination_class = None

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit-events.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                'timestamp',
                'event_type',
                'result',
                'actor_user_id_text',
                'actor_email',
                'actor_display_name',
                'actor_auth_source',
                'object_type',
                'object_id_text',
                'object_name',
                'source_number',
                'destination_number',
                'message',
                'metadata_json',
            ]
        )

        for event in self.get_queryset():
            writer.writerow(
                [
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.result,
                    event.actor_user_id_text,
                    event.actor_email,
                    event.actor_display_name,
                    event.actor_auth_source,
                    event.object_type,
                    event.object_id_text,
                    event.object_name,
                    event.source_number,
                    event.destination_number,
                    event.message,
                    json.dumps(event.metadata_json),
                ]
            )
        return response