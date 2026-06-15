from django.conf import settings
from django.utils import timezone

from audit.services import AuditService
from cucm.exceptions import CucmAuthenticationError, CucmNotFoundError, CucmUnavailableError
from cucm.factory import get_cucm_client
from dialplan.validators import validate_and_normalise_destination
from diversions.models import Diversion


CUCM_UNAVAILABLE_MESSAGE = (
    'CUCM is currently unavailable. Cached diversion information is displayed and updates are temporarily disabled.'
)


def cucm_status_value():
    try:
        get_cucm_client().health_check()
        return 'available'
    except Exception:
        return 'unavailable'


def validation_response(raw_destination: str):
    result = validate_and_normalise_destination(raw_destination)
    if result.is_valid:
        return {
            'is_valid': True,
            'original_input': result.original_input,
            'normalised_destination': result.normalised_e164,
            'destination_type': result.destination_type,
            'message': 'Destination is valid.',
        }
    return {
        'is_valid': False,
        'original_input': result.original_input,
        'error_code': result.error_code,
        'message': result.error_message,
    }


def _cache_refresh(diversion: Diversion, destination: str, *, update_user=None, mark_updated=False):
    now = timezone.now()
    fields = ['cached_current_destination', 'last_refreshed_at', 'updated_at']
    diversion.cached_current_destination = destination or ''
    diversion.last_refreshed_at = now
    if mark_updated and update_user is not None:
        diversion.last_updated_at = now
        diversion.last_updated_by_text = update_user.email
        fields.extend(['last_updated_at', 'last_updated_by_text'])
    diversion.save(update_fields=fields)


class DiversionAdminService:
    @staticmethod
    def validate_source_number(source_number: str):
        exists_in_app = Diversion.objects.filter(source_number=source_number).exists()
        try:
            directory_number = get_cucm_client().get_directory_number(source_number, settings.CUCM_ROUTE_PARTITION)
        except CucmNotFoundError:
            return {
                'is_valid': False,
                'source_number': source_number,
                'route_partition': settings.CUCM_ROUTE_PARTITION,
                'exists_in_cucm': False,
                'already_exists_in_app': exists_in_app,
                'current_destination': '',
            }

        return {
            'is_valid': not exists_in_app,
            'source_number': source_number,
            'route_partition': settings.CUCM_ROUTE_PARTITION,
            'exists_in_cucm': True,
            'already_exists_in_app': exists_in_app,
            'current_destination': directory_number.call_forward_all_destination or '',
        }


class DiversionUpdateService:
    @staticmethod
    def refresh_diversion(user, diversion: Diversion):
        try:
            directory_number = get_cucm_client().get_directory_number(diversion.source_number, diversion.source_partition)
        except (CucmUnavailableError, CucmAuthenticationError) as exc:
            AuditService.record_event(
                event_type='diversion.refresh.failure',
                result='failure',
                actor=user,
                object_type='diversion',
                object_id_text=str(diversion.pk),
                object_name=diversion.name,
                source_number=diversion.source_number,
                message='Diversion refresh failed.',
                metadata={'error': str(exc)},
            )
            return 503, {'result': 'failure', 'error_code': 'cucm_unavailable', 'message': CUCM_UNAVAILABLE_MESSAGE}

        raw_destination = directory_number.call_forward_all_destination or ''
        validation = validate_and_normalise_destination(raw_destination) if raw_destination else None
        cached_value = validation.normalised_e164 if validation and validation.is_valid else raw_destination
        _cache_refresh(diversion, cached_value)

        AuditService.record_event(
            event_type='diversion.refresh.success',
            result='success',
            actor=user,
            object_type='diversion',
            object_id_text=str(diversion.pk),
            object_name=diversion.name,
            source_number=diversion.source_number,
            destination_number=cached_value,
            message='Diversion refreshed successfully.',
        )
        return 200, {'result': 'success'}

    @staticmethod
    def update_destination(user, diversion: Diversion, raw_destination: str):
        validation = validate_and_normalise_destination(raw_destination)
        if not validation.is_valid:
            AuditService.record_event(
                event_type='diversion.destination_validation.failure',
                result='failure',
                actor=user,
                object_type='diversion',
                object_id_text=str(diversion.pk),
                object_name=diversion.name,
                source_number=diversion.source_number,
                destination_number=raw_destination,
                message='Diversion destination validation failed.',
                metadata={'error_code': validation.error_code},
            )
            return 400, validation_response(raw_destination)

        try:
            result = get_cucm_client().update_call_forward_all(
                diversion.source_number,
                diversion.source_partition,
                validation.normalised_e164,
            )
        except (CucmUnavailableError, CucmAuthenticationError) as exc:
            AuditService.record_event(
                event_type='diversion.destination_update.failure',
                result='failure',
                actor=user,
                object_type='diversion',
                object_id_text=str(diversion.pk),
                object_name=diversion.name,
                source_number=diversion.source_number,
                destination_number=validation.normalised_e164,
                message='Diversion update failed because CUCM is unavailable.',
                metadata={'error': str(exc)},
            )
            return 503, {'result': 'failure', 'error_code': 'cucm_unavailable', 'message': CUCM_UNAVAILABLE_MESSAGE}

        actual_destination = result.returned_destination or ''
        readback = validate_and_normalise_destination(actual_destination) if actual_destination else None
        if readback and readback.is_valid and readback.normalised_e164 == validation.normalised_e164:
            _cache_refresh(diversion, readback.normalised_e164, update_user=user, mark_updated=True)
            AuditService.record_event(
                event_type='diversion.destination_update.success',
                result='success',
                actor=user,
                object_type='diversion',
                object_id_text=str(diversion.pk),
                object_name=diversion.name,
                source_number=diversion.source_number,
                destination_number=readback.normalised_e164,
                message='Diversion updated successfully.',
            )
            return 200, {
                'result': 'success',
                'message': 'Diversion updated successfully.',
            }

        if readback and readback.is_valid:
            _cache_refresh(diversion, readback.normalised_e164)

        AuditService.record_event(
            event_type='diversion.destination_update.warning',
            result='warning',
            actor=user,
            object_type='diversion',
            object_id_text=str(diversion.pk),
            object_name=diversion.name,
            source_number=diversion.source_number,
            destination_number=actual_destination,
            message='Diversion update completed with a read-back mismatch.',
            metadata={
                'expected': validation.normalised_e164,
                'actual': actual_destination,
            },
        )
        return 409, {
            'result': 'failure',
            'error_code': 'cucm_readback_mismatch',
            'message': 'CUCM returned a different destination than expected. The cached state may have been refreshed.',
        }