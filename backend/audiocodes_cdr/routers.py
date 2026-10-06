# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

from audiocodes_cdr.constants import APP_LABEL, SOURCE_DB_ALIAS, SOURCE_MODEL_NAMES
from audiocodes_cdr.exceptions import SourceWriteForbidden


def is_source_model(model):
    meta = getattr(model, '_meta', None)
    return bool(meta and meta.app_label == APP_LABEL and meta.model_name in SOURCE_MODEL_NAMES)


class AudioCodesSourceRouter:
    """Route the unmanaged SDR/CDR models to the read-only source and keep everything else off it."""

    def db_for_read(self, model, **hints):
        if is_source_model(model):
            return SOURCE_DB_ALIAS
        return None

    def db_for_write(self, model, **hints):
        if is_source_model(model):
            raise SourceWriteForbidden('The AudioCodes source database is read-only.')
        return None

    def allow_relation(self, obj1, obj2, **hints):
        source1, source2 = is_source_model(obj1), is_source_model(obj2)
        if source1 or source2:
            return source1 and source2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == SOURCE_DB_ALIAS:
            return False
        if app_label == APP_LABEL and model_name and model_name.lower() in SOURCE_MODEL_NAMES:
            return False
        return None
