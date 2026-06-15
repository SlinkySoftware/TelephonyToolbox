from dataclasses import asdict, dataclass
import re


SANITIZE_PATTERN = re.compile(r'[\s()\-]+')
UNSUPPORTED_MESSAGE = 'Unsupported dial string. Enter an Australian FNN, mobile or +E.164 number.'
INTERNAL_EXTENSION_MESSAGE = 'Internal extensions are not permitted. Enter an Australian FNN, mobile or +E.164 number.'
SIP_URI_MESSAGE = 'SIP URIs are not permitted. Enter an Australian FNN, mobile or +E.164 number.'
INTERNATIONAL_MESSAGE = 'International numbers are not permitted. Enter an Australian FNN, mobile or +E.164 number.'


@dataclass(slots=True)
class NormalisedDestination:
    original_input: str
    stripped_input: str
    normalised_e164: str | None
    destination_type: str | None
    is_valid: bool
    error_code: str | None = None
    error_message: str | None = None

    def as_dict(self):
        return asdict(self)


def _invalid(raw_input, stripped_input, error_code, error_message):
    return NormalisedDestination(
        original_input=raw_input,
        stripped_input=stripped_input,
        normalised_e164=None,
        destination_type=None,
        is_valid=False,
        error_code=error_code,
        error_message=error_message,
    )


def _valid(original_input, stripped_input, normalised_e164, destination_type):
    return NormalisedDestination(
        original_input=original_input,
        stripped_input=stripped_input,
        normalised_e164=normalised_e164,
        destination_type=destination_type,
        is_valid=True,
    )


def _validate_e164(original_input, stripped_input):
    if not stripped_input.startswith('+61'):
        return _invalid(original_input, stripped_input, 'non_australian_e164', 'Only Australian +E.164 numbers are permitted.')

    national_digits = stripped_input[3:]
    if re.fullmatch(r'[2378]\d{8}', national_digits):
        return _valid(original_input, stripped_input, stripped_input, 'fnn')
    if re.fullmatch(r'4\d{8}', national_digits):
        return _valid(original_input, stripped_input, stripped_input, 'mobile')
    return _invalid(original_input, stripped_input, 'unsupported_dial_string', UNSUPPORTED_MESSAGE)


def _validate_national(original_input, stripped_input):
    if re.fullmatch(r'0[2378]\d{8}', stripped_input):
        return _valid(original_input, stripped_input, f'+61{stripped_input[1:]}', 'fnn')

    if re.fullmatch(r'04\d{8}', stripped_input):
        return _valid(original_input, stripped_input, f'+61{stripped_input[1:]}', 'mobile')

    if stripped_input.isdigit() and len(stripped_input) < 10:
        return _invalid(original_input, stripped_input, 'internal_extension_not_allowed', INTERNAL_EXTENSION_MESSAGE)

    return _invalid(original_input, stripped_input, 'unsupported_dial_string', UNSUPPORTED_MESSAGE)


def validate_and_normalise_destination(raw_input: str) -> NormalisedDestination:
    original_input = raw_input or ''
    stripped_input = SANITIZE_PATTERN.sub('', original_input.strip())

    if not stripped_input:
        return _invalid(original_input, stripped_input, 'destination_required', 'Destination is required.')

    if stripped_input.lower().startswith('sip:') or '@' in stripped_input:
        return _invalid(original_input, stripped_input, 'sip_uri_not_allowed', SIP_URI_MESSAGE)

    if stripped_input.startswith('0011'):
        return _invalid(original_input, stripped_input, 'international_not_allowed', INTERNATIONAL_MESSAGE)

    if not re.fullmatch(r'\+?\d+', stripped_input):
        return _invalid(original_input, stripped_input, 'unsupported_dial_string', UNSUPPORTED_MESSAGE)

    if stripped_input.startswith('+'):
        return _validate_e164(original_input, stripped_input)

    return _validate_national(original_input, stripped_input)