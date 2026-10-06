# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from zoneinfo import ZoneInfo

APP_LABEL = 'audiocodes_cdr'
SOURCE_DB_ALIAS = 'audiocodes_source'
SOURCE_MODEL_NAMES = frozenset({'sdr', 'cdr'})
ROUTER_PATH = 'audiocodes_cdr.routers.AudioCodesSourceRouter'

STATEMENT_TIMEOUT_MS = 60000
SOURCE_APPLICATION_NAME = 'telephony-toolbox-cdr'

SYDNEY = ZoneInfo('Australia/Sydney')
MAX_RANGE_MONTHS = 12

PAGE_SIZE_OPTIONS = (25, 50, 100, 250, 500)
DEFAULT_PAGE_SIZE = 100
HARD_MAX_PAGE_SIZE = 500

MATCH_MODES = ('exact', 'startswith', 'endswith', 'contains')
STATUS_FILTERS = ('all', 'successful', 'unsuccessful', 'unknown')

TERMINATION_FIELDS = (
    'ingressterminationreason',
    'egressterminationreason',
    'ingresssipterminationreason',
    'egresssipterminationreason',
)

USER_DEFINED_FIELD_KEYS = tuple(f'varcalluserdefined{index}' for index in range(1, 6))

MEDIA_QUALITY_METRICS = {
    'local_jitter': 'localjitter',
    'remote_jitter': 'remotejitter',
    'local_packet_loss': 'localpacketloss',
    'remote_packet_loss': 'remotepacketloss',
    'local_round_trip_delay': 'localroundtripdelay',
    'remote_round_trip_delay': 'remoteroundtripdelay',
}

# Upper bound on CDR legs returned for one session; protects against a degenerate shared sessionid.
MAX_CDRS_PER_SESSION = 1000
