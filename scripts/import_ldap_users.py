#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Bulk-create LDAP application users from a CSV file.

Each row of the CSV describes a single user and the access groups they should
belong to. The first column is the user's email address; every remaining,
non-empty column is an access group name. A user may belong to multiple groups.

    alice@example.com,Helpdesk,Reception
    bob@example.com,Engineering

For every row the script:

  1. Confirms the user does not already exist in the platform.
  2. Performs an LDAP lookup to confirm the user exists and is enabled.
  3. Confirms every named access group exists.

If any of those checks fail for a row, that user is reported as an error and
skipped; processing continues with the remaining rows. A user is only created
once all of their checks pass, and their group memberships are written in the
same database transaction.

Usage:
    python scripts/import_ldap_users.py users.csv

Run from the repository root (or anywhere) with the backend virtualenv active.
"""

import argparse
import csv
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / 'backend'


def bootstrap_django():
    """Make the Django project importable and initialise the app registry."""
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telephony_toolbox.settings')
    import django

    django.setup()


def read_rows(csv_path):
    """Yield (line_number, email, group_names) tuples from the CSV file.

    Blank lines and lines whose first cell begins with '#' are ignored. An
    optional header row (first cell equal to 'email', case-insensitive) is
    skipped automatically.
    """
    with open(csv_path, newline='', encoding='utf-8') as handle:
        reader = csv.reader(handle)
        for line_number, raw_row in enumerate(reader, start=1):
            cells = [cell.strip() for cell in raw_row]
            if not any(cells):
                continue
            if cells[0].startswith('#'):
                continue
            if line_number == 1 and cells[0].lower() == 'email':
                continue

            email = cells[0]
            # Preserve order while removing duplicates and empty group cells.
            group_names = list(dict.fromkeys(name for name in cells[1:] if name))
            yield line_number, email, group_names


def process_row(line_number, email, group_names, deps):
    """Validate and create a single user. Returns an error string or None."""
    User = deps['User']
    AccessGroup = deps['AccessGroup']
    UserGroupMembership = deps['UserGroupMembership']
    AuthSource = deps['AuthSource']
    UserRole = deps['UserRole']
    transaction = deps['transaction']
    ldap_provider = deps['ldap_provider']
    ExternalIdentityError = deps['ExternalIdentityError']

    normalized_email = User.objects.normalize_identity(email)

    if not normalized_email:
        return f'line {line_number}: missing email address.'

    if not group_names:
        return f'line {line_number} ({normalized_email}): no access groups listed.'

    # 1. Reject users that already exist in the platform.
    if User.objects.filter(email=normalized_email).exists():
        return f'line {line_number} ({normalized_email}): user already exists in the platform.'

    # 2. Resolve every access group; fail if any name is unknown.
    resolved_groups = []
    for name in group_names:
        try:
            resolved_groups.append(AccessGroup.objects.get(name=name))
        except AccessGroup.DoesNotExist:
            return f'line {line_number} ({normalized_email}): access group "{name}" not found.'

    # 3. Look the user up in LDAP; require an enabled, existing account.
    try:
        identity = ldap_provider.validate_user(normalized_email)
    except ExternalIdentityError as exc:
        return f'line {line_number} ({normalized_email}): LDAP lookup failed: {exc}'

    if not identity.exists:
        return f'line {line_number} ({normalized_email}): user not found in LDAP.'
    if not identity.enabled:
        return f'line {line_number} ({normalized_email}): LDAP account is disabled.'

    display_name = identity.display_name or identity.email or normalized_email

    # All checks passed: create the user and memberships atomically.
    with transaction.atomic():
        user = User.objects.create_user(
            email=identity.email or normalized_email,
            display_name=display_name,
            auth_source=AuthSource.LDAP,
            role=UserRole.STANDARD_USER,
            is_active=True,
            is_local=False,
        )
        UserGroupMembership.objects.bulk_create(
            UserGroupMembership(user=user, group=group) for group in resolved_groups
        )

    group_list = ', '.join(group.name for group in resolved_groups)
    print(f'Created {user.email} ({display_name}) in groups: {group_list}')
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Create LDAP application users and group memberships from a CSV file.',
    )
    parser.add_argument(
        'csv_file',
        help='Path to the CSV file. Each row: email,group[,group...].',
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_file).expanduser()
    if not csv_path.is_file():
        print(f'Error: CSV file not found: {csv_path}', file=sys.stderr)
        return 2

    bootstrap_django()

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db import transaction

    from access_groups.models import AccessGroup, UserGroupMembership
    from accounts.models import AuthSource, UserRole
    from accounts.services import ExternalIdentityError, LdapIdentityProvider

    if not settings.LDAP_SERVER_URI:
        print(
            'Error: LDAP is not configured (LDAP_SERVER_URI is empty). '
            'Set the LDAP_* environment variables before running this script.',
            file=sys.stderr,
        )
        return 2

    deps = {
        'User': get_user_model(),
        'AccessGroup': AccessGroup,
        'UserGroupMembership': UserGroupMembership,
        'AuthSource': AuthSource,
        'UserRole': UserRole,
        'transaction': transaction,
        'ldap_provider': LdapIdentityProvider(),
        'ExternalIdentityError': ExternalIdentityError,
    }

    created = 0
    errors = []
    for line_number, email, group_names in read_rows(csv_path):
        error = process_row(line_number, email, group_names, deps)
        if error:
            errors.append(error)
            print(f'ERROR: {error}', file=sys.stderr)
        else:
            created += 1

    print(f'\nDone. Created {created} user(s), {len(errors)} error(s).')
    if errors:
        print('\nErrors:', file=sys.stderr)
        for error in errors:
            print(f'  - {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
