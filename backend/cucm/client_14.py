# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from cucm.client_zeep import ZeepCucmClient


class Cucm14Client(ZeepCucmClient):
    version = '14'