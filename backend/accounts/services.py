# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from dataclasses import dataclass
from functools import lru_cache
import logging
from urllib.parse import urlencode

from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from ldap3 import ALL, SAFE_SYNC, Connection, Server
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars
import requests

from accounts.models import AuthSource


logger = logging.getLogger(__name__)
User = get_user_model()


class ExternalIdentityError(Exception):
    """Base external identity exception."""


class ExternalIdentityUnavailableError(ExternalIdentityError):
    """Raised when the configured identity provider is unavailable."""


@dataclass(slots=True)
class IdentityValidationResult:
    exists: bool
    provider: str
    email: str
    display_name: str = ''
    username: str = ''
    enabled: bool = True

    def as_dict(self):
        return {
            'exists': self.exists,
            'provider': self.provider,
            'email': self.email,
            'display_name': self.display_name,
            'username': self.username,
            'enabled': self.enabled,
        }


def normalize_email(email: str) -> str:
    return (email or '').strip().lower()


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'active'}


class LdapIdentityProvider:
    def _server(self):
        return Server(settings.LDAP_SERVER_URI, get_info=ALL)

    def _connect_as_service_account(self):
        return Connection(
            self._server(),
            user=settings.LDAP_BIND_DN,
            password=settings.LDAP_BIND_PASSWORD,
            auto_bind=True,
            client_strategy=SAFE_SYNC,
            raise_exceptions=True,
        )

    def _search(self, email: str):
        email = normalize_email(email)
        attributes = [settings.LDAP_USER_EMAIL_ATTRIBUTE, settings.LDAP_USER_DISPLAY_NAME_ATTRIBUTE]
        if settings.LDAP_USER_ENABLED_ATTRIBUTE:
            attributes.append(settings.LDAP_USER_ENABLED_ATTRIBUTE)

        # Build LDAP search filter: either custom filter template (with %email placeholder)
        # or default email-based search. The %email placeholder is replaced with the escaped
        # email address to prevent LDAP injection attacks.
        if settings.LDAP_GROUP_SEARCH_FILTER:
            # Use custom group search filter with %email placeholder replaced
            search_filter = settings.LDAP_GROUP_SEARCH_FILTER.replace('%email', escape_filter_chars(email))
        else:
            # Default: search by email attribute only
            search_filter = f'({settings.LDAP_USER_EMAIL_ATTRIBUTE}={escape_filter_chars(email)})'

        with self._connect_as_service_account() as conn:
            conn.search(
                settings.LDAP_USER_SEARCH_BASE,
                search_filter,
                attributes=attributes,
            )
            if not conn.entries:
                return None
            return conn.entries[0]

    def validate_user(self, email: str) -> IdentityValidationResult:
        try:
            entry = self._search(email)
        except LDAPException as exc:
            raise ExternalIdentityUnavailableError(str(exc)) from exc

        if entry is None:
            return IdentityValidationResult(False, 'ldap', normalize_email(email), '', '', False)

        enabled = True
        if settings.LDAP_USER_ENABLED_ATTRIBUTE:
            enabled = _truthy(getattr(entry, settings.LDAP_USER_ENABLED_ATTRIBUTE).value)

        actual_email = getattr(entry, settings.LDAP_USER_EMAIL_ATTRIBUTE).value or normalize_email(email)
        display_name = getattr(entry, settings.LDAP_USER_DISPLAY_NAME_ATTRIBUTE).value or actual_email
        return IdentityValidationResult(True, 'ldap', normalize_email(actual_email), display_name, normalize_email(actual_email), enabled)

    def authenticate_user(self, email: str, password: str) -> IdentityValidationResult:
        try:
            entry = self._search(email)
        except LDAPException as exc:
            raise ExternalIdentityUnavailableError(str(exc)) from exc

        if entry is None:
            return IdentityValidationResult(False, 'ldap', normalize_email(email), enabled=False)

        try:
            Connection(
                self._server(),
                user=entry.entry_dn,
                password=password,
                auto_bind=True,
                client_strategy=SAFE_SYNC,
                raise_exceptions=True,
            ).unbind()
        except LDAPException:
            return IdentityValidationResult(False, 'ldap', normalize_email(email), enabled=False)

        return self.validate_user(email)


class EntraIdentityProvider:
    token_url_template = 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    users_url = 'https://graph.microsoft.com/v1.0/users'

    def _token(self):
        response = requests.post(
            self.token_url_template.format(tenant=settings.ENTRA_TENANT_ID),
            data={
                'client_id': settings.ENTRA_CLIENT_ID,
                'client_secret': settings.ENTRA_CLIENT_SECRET,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials',
            },
            timeout=30,
        )
        if not response.ok:
            raise ExternalIdentityUnavailableError('Unable to acquire Microsoft Graph access token.')
        return response.json()['access_token']

    def validate_user(self, email: str) -> IdentityValidationResult:
        email = normalize_email(email)
        response = requests.get(
            self.users_url,
            headers={'Authorization': f'Bearer {self._token()}'},
            params={
                '$filter': f"mail eq '{email}' or userPrincipalName eq '{email}'",
                '$select': 'mail,displayName,userPrincipalName,accountEnabled',
            },
            timeout=30,
        )
        if not response.ok:
            raise ExternalIdentityUnavailableError('Unable to query Microsoft Graph for user validation.')

        payload = response.json().get('value', [])
        if not payload:
            return IdentityValidationResult(False, 'entra', email, '', '', False)

        user = payload[0]
        actual_email = normalize_email(user.get('mail') or user.get('userPrincipalName') or email)
        display_name = user.get('displayName') or actual_email
        username = user.get('userPrincipalName') or actual_email
        enabled = bool(user.get('accountEnabled', True))
        return IdentityValidationResult(True, 'entra', actual_email, display_name, username, enabled)


@lru_cache(maxsize=1)
def get_entra_oauth_client():
    oauth = OAuth()
    oauth.register(
        'entra',
        client_id=settings.ENTRA_CLIENT_ID,
        client_secret=settings.ENTRA_CLIENT_SECRET,
        server_metadata_url=f'https://login.microsoftonline.com/{settings.ENTRA_TENANT_ID}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile email'},
    )
    return oauth.create_client('entra')


class EntraOidcService:
    @staticmethod
    def authorize_redirect(request):
        client = get_entra_oauth_client()
        redirect_uri = settings.ENTRA_REDIRECT_URI or request.build_absolute_uri(reverse('auth-entra-callback'))
        return client.authorize_redirect(request, redirect_uri)

    @staticmethod
    def handle_callback(request) -> IdentityValidationResult:
        client = get_entra_oauth_client()
        token = client.authorize_access_token(request)
        claims = token.get('userinfo') or client.parse_id_token(request, token)
        if claims is None:
            raise ExternalIdentityUnavailableError('Unable to extract user claims from Entra callback.')

        email = normalize_email(claims.get('email') or claims.get('preferred_username') or '')
        if not email:
            raise ExternalIdentityUnavailableError('Entra callback did not include a usable email address.')

        display_name = claims.get('name') or email
        username = claims.get('preferred_username') or email
        return IdentityValidationResult(True, 'entra', email, display_name, username, True)


class IdentityValidationService:
    @staticmethod
    def current_provider():
        if settings.AUTH_MODE == 'ldap':
            return LdapIdentityProvider()
        if settings.AUTH_MODE == 'entra':
            return EntraIdentityProvider()
        raise ValueError(f'Unsupported AUTH_MODE: {settings.AUTH_MODE}')

    @classmethod
    def validate_user(cls, email: str) -> IdentityValidationResult:
        return cls.current_provider().validate_user(email)


def sync_external_user(identity: IdentityValidationResult):
    try:
        user = User.objects.get(email=identity.email)
    except User.DoesNotExist:
        return None

    user.display_name = identity.display_name or user.display_name
    user.auth_source = identity.provider
    user.save(update_fields=['display_name', 'auth_source', 'updated_at'])
    return user


def frontend_error_redirect(message: str) -> str:
    return '/login?' + urlencode({'error': message})