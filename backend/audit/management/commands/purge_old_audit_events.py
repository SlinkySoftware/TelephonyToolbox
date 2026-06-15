from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditEvent


class Command(BaseCommand):
    help = 'Deletes audit events older than the configured retention period.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=settings.AUDIT_RETENTION_DAYS)
        deleted, _ = AuditEvent.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} audit events older than {cutoff.isoformat()}.'))