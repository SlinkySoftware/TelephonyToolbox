# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAppAdmin
from health.services import build_admin_health_report


class HealthzView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'})


class AdminHealthView(APIView):
    permission_classes = [IsAppAdmin]

    def get(self, request):
        return Response(build_admin_health_report())