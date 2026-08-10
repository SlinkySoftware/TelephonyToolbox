# Bulk User Import

The `scripts/import_ldap_users.py` script bulk-creates LDAP application users
and their access-group memberships from a CSV file. It is a standalone script
that lives in the `scripts/` directory and talks directly to the Telephony
Toolbox database and the configured LDAP directory.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [CSV Format](#csv-format)
4. [Usage](#usage)
5. [How It Works](#how-it-works)
6. [Validation and Errors](#validation-and-errors)
7. [Exit Codes](#exit-codes)
8. [Examples](#examples)

---

## Overview

The script reads a CSV file describing one user per row, looks each user up in
LDAP, and creates a corresponding Telephony Toolbox application user assigned to
the listed access groups.

Created users are given:

- `auth_source` = `ldap`
- `role` = Standard User
- `is_active` = `true`
- `is_local` = `false`
- `display_name` sourced from LDAP (falling back to the email address)

Users are validated before any record is written. When a row fails validation
that single user is reported as an error and skipped; the remaining rows are
still processed. Each successful user and their memberships are written in a
single database transaction.

---

## Prerequisites

- The backend virtual environment must be active (so Django and its
  dependencies are importable).
- LDAP must be configured via the `LDAP_*` environment variables. The script
  refuses to run if `LDAP_SERVER_URI` is empty. See
  [CONFIGURATION.md](CONFIGURATION.md) for the full list of LDAP settings.
- The access groups referenced in the CSV must already exist in the platform.
  The script never creates groups.

---

## CSV Format

Each row describes a single user:

- The **first column** is the user's email address.
- **Every remaining, non-empty column** is an access group name.

A user may belong to multiple groups, so list as many group columns as needed.

```csv
alice@example.com,Helpdesk,Reception
bob@example.com,Engineering
```

Formatting rules:

- Blank lines are ignored.
- Lines whose first cell begins with `#` are treated as comments and ignored.
- An optional header row is skipped automatically when its first cell is
  `email` (case-insensitive).
- Duplicate and empty group cells within a row are removed; group order is
  otherwise preserved.
- Email addresses are normalised (trimmed and lower-cased) before use.

---

## Usage

Run the script from the repository root with the backend virtual environment
active, passing the CSV path on the command line:

```bash
source .venv/bin/activate
python scripts/import_ldap_users.py users.csv
```

The CSV path is the only argument. `~` in the path is expanded.

```
usage: import_ldap_users.py [-h] csv_file
```

---

## How It Works

For each row the script performs the following steps in order:

1. Normalises the email address.
2. Confirms at least one access group is listed.
3. Confirms the user does **not** already exist in the platform.
4. Resolves every named access group, failing if any name is unknown.
5. Performs an LDAP lookup and requires an existing, enabled account.
6. Creates the user and their group memberships atomically.

Because the user record is only created after every check passes, a failed row
never leaves a partially-created user behind.

---

## Validation and Errors

A user is reported as an error and skipped when any of the following are true:

- **Missing email** — the row has no email address in the first column.
- **No access groups** — the row lists no group names.
- **User already exists** — a platform user with that email is already present.
- **Access group not found** — one of the named groups does not exist.
- **LDAP lookup failed** — the LDAP directory could not be reached or the query
  errored.
- **User not found in LDAP** — LDAP returned no matching account.
- **LDAP account is disabled** — LDAP returned a disabled account.

Errors are printed to standard error as they occur and again in a summary at the
end of the run. Successful creations are printed to standard output.

---

## Exit Codes

| Code | Meaning                                                             |
| ---- | ------------------------------------------------------------------- |
| `0`  | All rows were processed and every user was created successfully.    |
| `1`  | The run completed but one or more rows failed validation.           |
| `2`  | The run could not start (CSV file missing, or LDAP not configured). |

---

## Examples

Import users from a CSV file:

```bash
python scripts/import_ldap_users.py users.csv
```

Example `users.csv`:

```csv
# email,group[,group...]
alice@example.com,Helpdesk,Reception
bob@example.com,Engineering
carol@example.com,Helpdesk
```

Example output:

```
Created alice@example.com (Alice Smith) in groups: Helpdesk, Reception
Created bob@example.com (Bob Jones) in groups: Engineering
ERROR: line 4 (carol@example.com): user not found in LDAP.

Done. Created 2 user(s), 1 error(s).

Errors:
  - line 4 (carol@example.com): user not found in LDAP.
```
