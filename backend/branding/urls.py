# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from django.urls import path

from branding.views import BrandingAssetView


urlpatterns = [
    path('branding/<slug:slug>/', BrandingAssetView.as_view(), name='branding-asset'),
]
