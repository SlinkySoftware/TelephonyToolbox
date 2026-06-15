# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from dataclasses import dataclass, field


@dataclass(slots=True)
class CucmDirectoryNumber:
    pattern: str
    route_partition: str
    description: str | None = None
    alerting_name: str | None = None
    ascii_alerting_name: str | None = None
    call_forward_all_destination: str | None = None
    calling_search_space: str | None = None
    secondary_calling_search_space: str | None = None
    raw_payload: dict = field(default_factory=dict)

    @property
    def line_name(self) -> str:
        return self.alerting_name or self.ascii_alerting_name or self.description or self.pattern


@dataclass(slots=True)
class CucmUpdateResult:
    success: bool
    pattern: str
    route_partition: str
    returned_destination: str | None = None
    message: str = ''
    raw_payload: dict = field(default_factory=dict)


@dataclass(slots=True)
class CucmHealthResult:
    available: bool
    status: str
    message: str = ''
    version: str | None = None