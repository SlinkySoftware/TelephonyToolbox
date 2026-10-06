# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest
from cryptography.fernet import Fernet

from audiocodes_cdr.crypto import KEY_INVALID, KEY_MISSING, KEY_OK, decrypt_secret, encrypt_secret, key_status
from audiocodes_cdr.exceptions import SourceConfigurationError


def test_round_trip(encryption_key):
    token = encrypt_secret('s3cret-pässword')

    assert 's3cret' not in token
    assert decrypt_secret(token) == 's3cret-pässword'


def test_rotation_first_key_encrypts_all_keys_decrypt(settings):
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    settings.CDR_SOURCE_ENCRYPTION_KEY = old_key
    old_token = encrypt_secret('legacy')

    settings.CDR_SOURCE_ENCRYPTION_KEY = f'{new_key}, {old_key}'
    assert decrypt_secret(old_token) == 'legacy'
    new_token = encrypt_secret('fresh')

    settings.CDR_SOURCE_ENCRYPTION_KEY = new_key
    assert decrypt_secret(new_token) == 'fresh'


def test_missing_key_fails_closed(settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = ''

    assert key_status() == KEY_MISSING
    with pytest.raises(SourceConfigurationError) as exc_info:
        encrypt_secret('x')
    assert exc_info.value.error_code == 'encryption_key_missing'


def test_invalid_key_fails_closed(settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = 'not-a-valid-key'

    assert key_status() == KEY_INVALID
    with pytest.raises(SourceConfigurationError) as exc_info:
        decrypt_secret('anything')
    assert exc_info.value.error_code == 'encryption_key_invalid'


def test_wrong_key_cannot_decrypt(settings):
    settings.CDR_SOURCE_ENCRYPTION_KEY = Fernet.generate_key().decode()
    token = encrypt_secret('x')
    settings.CDR_SOURCE_ENCRYPTION_KEY = Fernet.generate_key().decode()

    assert key_status() == KEY_OK
    with pytest.raises(SourceConfigurationError) as exc_info:
        decrypt_secret(token)
    assert exc_info.value.error_code == 'credential_decrypt_failed'
