import pytest

from dialplan.validators import validate_and_normalise_destination


@pytest.mark.parametrize(
    ('raw_input', 'expected'),
    [
        ('02 9999 1234', '+61299991234'),
        ('(02) 9999 1234', '+61299991234'),
        ('0412 345 678', '+61412345678'),
        ('+61299991234', '+61299991234'),
    ],
)
def test_valid_destinations_are_normalised(raw_input, expected):
    result = validate_and_normalise_destination(raw_input)

    assert result.is_valid is True
    assert result.normalised_e164 == expected


@pytest.mark.parametrize(
    ('raw_input', 'error_code'),
    [
        ('12345', 'internal_extension_not_allowed'),
        ('001144123456789', 'international_not_allowed'),
        ('+44123456789', 'non_australian_e164'),
        ('sip:user@example.com', 'sip_uri_not_allowed'),
        ('', 'destination_required'),
    ],
)
def test_invalid_destinations_are_rejected(raw_input, error_code):
    result = validate_and_normalise_destination(raw_input)

    assert result.is_valid is False
    assert result.error_code == error_code