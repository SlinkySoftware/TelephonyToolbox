# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

class CucmError(Exception):
    """Base CUCM exception."""


class CucmUnavailableError(CucmError):
    """Raised when CUCM cannot be reached."""


class CucmAuthenticationError(CucmError):
    """Raised when CUCM rejects credentials."""


class CucmNotFoundError(CucmError):
    """Raised when a CUCM directory number does not exist."""