# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

import os


TRUE_VALUES = {'1', 'true', 'yes', 'on'}


def load_env_file(path):
    try:
        with open(path, encoding='utf-8') as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                if not key:
                    continue

                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                os.environ.setdefault(key, value)
    except FileNotFoundError:
        return


def env_str(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def env_int(name, default=0):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return int(value)


def env_list(name, default=''):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]