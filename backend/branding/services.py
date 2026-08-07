# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import base64
import mimetypes
from pathlib import Path

from django.conf import settings

# Maps a public branding asset slug to the Django setting that holds an optional
# absolute filesystem path override. Slugs are the only values accepted by the
# serving view, so this mapping doubles as the allow-list.
BRANDING_ASSET_SETTINGS = {
    'header-logo': 'BRAND_HEADER_LOGO',
    'login-logo': 'BRAND_LOGIN_LOGO',
    'favicon': 'BRAND_FAVICON',
}

# 1x1 fully transparent PNG. Served whenever an asset has no configured override
# (or the configured file is missing/unreadable) so branding is blank by default.
TRANSPARENT_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
)


def resolve_branding_asset(slug):
    """Return the readable file path configured for ``slug``, or ``None``.

    The path is sourced from a trusted deployment setting (env / backend.env),
    never from client input, so the only checks required are existence and that
    the target is a regular readable file.
    """
    setting_name = BRANDING_ASSET_SETTINGS.get(slug)
    if setting_name is None:
        return None

    configured = (getattr(settings, setting_name, '') or '').strip()
    if not configured:
        return None

    path = Path(configured)
    if not path.is_file():
        return None

    return path


def guess_content_type(path):
    content_type, _ = mimetypes.guess_type(str(path))
    return content_type or 'application/octet-stream'
