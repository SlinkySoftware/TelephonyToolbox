# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import pytest

from branding.services import TRANSPARENT_PNG


@pytest.fixture
def png_file(tmp_path):
    path = tmp_path / 'logo.png'
    path.write_bytes(b'\x89PNG\r\n\x1a\ncustom-branding-bytes')
    return path


def test_unknown_asset_returns_404(api_client):
    response = api_client.get('/api/branding/unknown/')

    assert response.status_code == 404


def test_default_asset_is_blank_transparent_png(api_client):
    response = api_client.get('/api/branding/header-logo/')

    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png'
    assert response.content == TRANSPARENT_PNG


def test_default_asset_is_unauthenticated(api_client):
    response = api_client.get('/api/branding/favicon/')

    assert response.status_code == 200


def test_configured_override_is_served(api_client, settings, png_file):
    settings.BRAND_LOGIN_LOGO = str(png_file)

    response = api_client.get('/api/branding/login-logo/')

    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png'
    assert b''.join(response.streaming_content) == png_file.read_bytes()


def test_missing_override_file_falls_back_to_blank(api_client, settings, tmp_path):
    settings.BRAND_HEADER_LOGO = str(tmp_path / 'does-not-exist.png')

    response = api_client.get('/api/branding/header-logo/')

    assert response.status_code == 200
    assert response.content == TRANSPARENT_PNG
