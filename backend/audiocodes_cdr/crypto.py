# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Credential encryption for source profiles.

``CDR_SOURCE_ENCRYPTION_KEY`` holds one or more comma-separated Fernet keys. The first key
encrypts; every key can decrypt, which allows key rotation. A missing or invalid key fails closed.
"""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

from audiocodes_cdr.exceptions import SourceConfigurationError

KEY_OK = 'ok'
KEY_MISSING = 'missing'
KEY_INVALID = 'invalid'


def _configured_keys():
    raw = getattr(settings, 'CDR_SOURCE_ENCRYPTION_KEY', '') or ''
    return [key.strip() for key in raw.split(',') if key.strip()]


def _build_fernets(keys):
    return [Fernet(key.encode('ascii')) for key in keys]


def key_status():
    keys = _configured_keys()
    if not keys:
        return KEY_MISSING
    try:
        _build_fernets(keys)
    except (ValueError, TypeError, UnicodeEncodeError):
        return KEY_INVALID
    return KEY_OK


def _multi_fernet():
    keys = _configured_keys()
    if not keys:
        raise SourceConfigurationError('The credential encryption key is not configured.', 'encryption_key_missing')
    try:
        return MultiFernet(_build_fernets(keys))
    except (ValueError, TypeError, UnicodeEncodeError):
        raise SourceConfigurationError('The credential encryption key is invalid.', 'encryption_key_invalid') from None


def encrypt_secret(plaintext):
    return _multi_fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_secret(token):
    fernet = _multi_fernet()
    try:
        return fernet.decrypt(token.encode('ascii')).decode('utf-8')
    except (InvalidToken, UnicodeError):
        raise SourceConfigurationError(
            'The stored source credential cannot be decrypted with the configured key.',
            'credential_decrypt_failed',
        ) from None
