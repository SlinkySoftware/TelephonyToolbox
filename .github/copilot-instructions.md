Build Telephony Toolbox as a Quasar frontend and Django REST Framework backend.

Do not use Django Admin.

Use Django cookie-based session authentication with CSRF protection.

Use a custom Django user model from project creation.

Email address is the canonical user identifier.

Support only one configured external auth provider per deployment: Entra or LDAP. Local fallback users are always supported.

Application roles are Standard User and App Admin only.

Application groups are local only. Users can belong to multiple groups. A diversion belongs to exactly one group.

Cisco UCM is the source of truth for live diversion state.

The app manages only Call Forward All for CUCM Directory Numbers.

Source DNs are globally unique and always use the configured route partition, default INTERNAL.

Destination validation is hard-coded. Allow only Australian FNN, Australian mobile and Australian +E.164. Normalise all valid destinations to Australian +E.164 before writing to CUCM.

Never allow blank destinations, internal extensions, international numbers or SIP URIs.

On destination update, write to CUCM via AXL, read back from CUCM, revalidate the returned value and only show clean success if it matches expected +E.164.

If CUCM is unavailable, allow login and cached state viewing, but block edits.

Diversion deletion deletes only the local app record and never modifies CUCM.

Users are hard deleted. Audit records must store actor/user details as text fields, not foreign keys.

Audit retention is 90 days. App Admins can export audit logs to CSV.

Deployment target is bare-metal RHEL9 with nginx serving Quasar static files and proxy_pass to Django/gunicorn. PostgreSQL is the database.
