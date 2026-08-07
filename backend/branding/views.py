# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.http import FileResponse, Http404, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from branding.services import (
    BRANDING_ASSET_SETTINGS,
    TRANSPARENT_PNG,
    guess_content_type,
    resolve_branding_asset,
)


class BrandingAssetView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, slug):
        if slug not in BRANDING_ASSET_SETTINGS:
            raise Http404('Unknown branding asset.')

        path = resolve_branding_asset(slug)
        if path is None:
            response = HttpResponse(TRANSPARENT_PNG, content_type='image/png')
        else:
            response = FileResponse(path.open('rb'), content_type=guess_content_type(path))

        # Encourage revalidation so an updated override (env change + restart)
        # is picked up without stale-favicon caching getting in the way.
        response['Cache-Control'] = 'no-cache'
        return response
