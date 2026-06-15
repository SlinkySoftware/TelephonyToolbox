# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from requests import Session

from cucm.client_zeep import LegacyCucmTlsAdapter, ZeepCucmClient


class Cucm105Client(ZeepCucmClient):
    version = '10.5'
    legacy_ssl_ciphers = 'DEFAULT:@SECLEVEL=0'

    def _configure_session(self, session: Session) -> None:
        session.mount('https://', LegacyCucmTlsAdapter(ciphers=self.legacy_ssl_ciphers))