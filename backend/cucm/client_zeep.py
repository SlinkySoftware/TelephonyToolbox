# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import ssl
from pathlib import Path

import requests
from django.conf import settings
from requests import Session
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from zeep import Client, Settings as ZeepSettings
from zeep.exceptions import Fault, TransportError
from zeep.transports import Transport

from cucm.client import CucmClient
from cucm.exceptions import CucmAuthenticationError, CucmNotFoundError, CucmUnavailableError
from cucm.schemas import CucmDirectoryNumber, CucmHealthResult, CucmUpdateResult


class LegacyCucmTlsAdapter(HTTPAdapter):
    def __init__(self, ciphers: str, **kwargs):
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.set_ciphers(ciphers)
        self._ssl_context.check_hostname = False
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs['ssl_context'] = self._ssl_context
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs['ssl_context'] = self._ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)


class ZeepCucmClient(CucmClient):
    version = None

    def __init__(self, host: str | None = None, username: str | None = None, password: str | None = None):
        self.host = host or settings.CUCM_AXL_HOST
        self.username = username or settings.CUCM_AXL_USERNAME
        self.password = password or settings.CUCM_AXL_PASSWORD
        self._service = self._build_service()

    def _build_service(self):
        wsdl_path = Path(settings.REPO_ROOT) / 'wsdl' / self.version / 'AXLAPI.wsdl'
        session = self._build_session()
        transport = Transport(session=session, timeout=30)
        client = Client(str(wsdl_path), transport=transport, settings=ZeepSettings(strict=False, xml_huge_tree=True))
        return client.create_service('{http://www.cisco.com/AXLAPIService/}AXLAPIBinding', f'https://{self.host}:8443/axl/')

    def _build_session(self) -> Session:
        session: Session = requests.Session()
        session.auth = HTTPBasicAuth(self.username, self.password)
        session.verify = settings.CUCM_AXL_VERIFY_TLS
        self._configure_session(session)
        return session

    def _configure_session(self, session: Session) -> None:
        return None

    def _route_partition_fk(self, value):
        if not value:
            return None
        return {'_value_1': value}

    def _field_value(self, container, key, default=None):
        if container is None:
            return default
        if isinstance(container, dict):
            return container.get(key, default)
        return getattr(container, key, default)

    def _parse_line(self, response, pattern, route_partition):
        line = self._field_value(response, 'return', {})
        call_forward_all = self._field_value(line, 'callForwardAll', {}) or {}
        description = self._field_value(line, 'description')
        alerting_name = self._field_value(line, 'alertingName')
        ascii_alerting_name = self._field_value(line, 'asciiAlertingName')
        destination = self._field_value(call_forward_all, 'destination')
        css = self._field_value(call_forward_all, 'callingSearchSpaceName')
        secondary_css = self._field_value(call_forward_all, 'secondaryCallingSearchSpaceName')
        return CucmDirectoryNumber(
            pattern=pattern,
            route_partition=route_partition,
            description=description,
            alerting_name=alerting_name,
            ascii_alerting_name=ascii_alerting_name,
            call_forward_all_destination=destination,
            calling_search_space=self._fk_value(css),
            secondary_calling_search_space=self._fk_value(secondary_css),
            raw_payload={'line': line},
        )

    def _fk_value(self, raw_value):
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            return raw_value
        value = getattr(raw_value, '_value_1', None)
        if value:
            return value
        if isinstance(raw_value, dict):
            return raw_value.get('_value_1') or raw_value.get('value')
        return str(raw_value)

    def get_directory_number(self, pattern: str, route_partition: str) -> CucmDirectoryNumber:
        try:
            response = self._service.getLine(
                pattern=pattern,
                routePartitionName=self._route_partition_fk(route_partition),
                returnedTags={
                    'pattern': '',
                    'description': '',
                    'alertingName': '',
                    'asciiAlertingName': '',
                    'routePartitionName': '',
                    'callForwardAll': {
                        'destination': '',
                        'callingSearchSpaceName': '',
                        'secondaryCallingSearchSpaceName': '',
                    },
                },
            )
        except Fault as exc:
            message = str(exc)
            if 'Item not valid' in message or 'was not found' in message:
                raise CucmNotFoundError(message) from exc
            if '401' in message or 'Unauthorized' in message:
                raise CucmAuthenticationError(message) from exc
            raise CucmUnavailableError(message) from exc
        except (TransportError, RequestException) as exc:
            raise CucmUnavailableError(str(exc)) from exc

        return self._parse_line(response, pattern, route_partition)

    def update_call_forward_all(self, pattern: str, route_partition: str, destination: str) -> CucmUpdateResult:
        current = self.get_directory_number(pattern, route_partition)

        try:
            response = self._service.updateLine(
                pattern=pattern,
                routePartitionName=self._route_partition_fk(route_partition),
                callForwardAll={
                    'callingSearchSpaceName': self._route_partition_fk(current.calling_search_space),
                    'secondaryCallingSearchSpaceName': self._route_partition_fk(current.secondary_calling_search_space),
                    'destination': destination,
                },
            )
        except Fault as exc:
            message = str(exc)
            if '401' in message or 'Unauthorized' in message:
                raise CucmAuthenticationError(message) from exc
            raise CucmUnavailableError(message) from exc
        except (TransportError, RequestException) as exc:
            raise CucmUnavailableError(str(exc)) from exc

        refreshed = self.get_directory_number(pattern, route_partition)
        return CucmUpdateResult(
            success=True,
            pattern=pattern,
            route_partition=route_partition,
            returned_destination=refreshed.call_forward_all_destination,
            message='Call Forward All updated successfully.',
            raw_payload={'response': response},
        )

    def health_check(self) -> CucmHealthResult:
        try:
            response = self._service.getCCMVersion()
        except Fault as exc:
            message = str(exc)
            if '401' in message or 'Unauthorized' in message:
                raise CucmAuthenticationError(message) from exc
            raise CucmUnavailableError(message) from exc
        except (TransportError, RequestException) as exc:
            raise CucmUnavailableError(str(exc)) from exc

        version = getattr(getattr(response, 'return', None), 'componentVersion', None)
        if version is None and isinstance(response, dict):
            version = response.get('return', {}).get('componentVersion')

        return CucmHealthResult(available=True, status='ok', version=str(version) if version else self.version)