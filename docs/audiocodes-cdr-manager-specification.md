# AudioCodes CDR Module for Telephony Toolbox
## Integration Specification

### 1. Purpose

Implement an administrator-only, read-only module within the existing Telephony Toolbox application for searching, reviewing and analysing AudioCodes Session Detail Records (SDRs) and their associated Call Detail Records (CDRs).

The module must use the existing Telephony Toolbox Quasar/Vue frontend, Django REST Framework backend, authentication and session handling, role/permission model, application database, logging, health checks, and deployment. It is not a separate application and must not add a second login flow, local break-glass account, standalone web server, or independent deployment stack.

The existing Telephony Toolbox application database is the sole store for module configuration and application-owned state. The AudioCodes SDR/CDR database remains a separately configured external data source and must be accessed read-only at all times. The module must not copy SDR or CDR records into the application database.

An AudioCodes SDR represents the overall call session. CDRs represent individual call legs handled by the SBC. One SDR can therefore have zero, one, two or more associated CDRs.

AudioCodes documentation states that the SBC generates CDRs for incoming and outgoing call legs, and may create additional outgoing CDRs for alternate destinations, call forking, cancelled destinations or unsuccessful routing attempts. The implementation must never assume that a session has exactly two CDRs.

The module is intended for:

- call troubleshooting;
- call routing analysis;
- number manipulation analysis;
- unsuccessful-call investigation;
- media-quality investigation;
- traffic and success-rate reporting.

---

# 2. Technology and integration standards

## 2.1 Backend

Use the existing Telephony Toolbox Python, Django, Django REST Framework, ORM, database configuration, and Gunicorn stack. Do not create a separate backend project, settings module, database, service, or dependency environment for this feature.

Do not use:

- FastAPI;
- Flask;
- JWT authentication;
- Django Admin as the user interface;
- direct source-data modification;
- client-side querying of PostgreSQL.

## 2.2 Frontend

Use the existing Quasar/Vue 3 frontend, router, Pinia stores, API client, shared components, styling and build. Integrate with these rather than introduce a standalone frontend. Preserve the specified search, detail and statistics behaviour. Any additional chart dependency must follow the repository’s existing dependency conventions.

## 2.3 Production platform

Follow the existing Telephony Toolbox production and development deployment model (RHEL 9, systemd, Gunicorn, Nginx and the configured TLS-termination path). This module must not require a separate service, virtual environment, hostname, reverse-proxy site, or frontend build/deployment.

---

# 3. Application routes and URL structure

The module is reached through the existing Telephony Toolbox SPA and API host, uses the existing frontend base path and API prefix, and relies on the current history-mode fallback and reverse-proxy configuration. Its frontend base route is `/admin/cdr` and its API namespace is `/api/admin/cdr/`. Do not add an independent API prefix or deployment mount or implement a new login route.


---

# 4. TLS and reverse-proxy handling

Use the existing Telephony Toolbox TLS termination, proxy-header, allowed-host, CSRF-origin, and secure-cookie configuration. Do not redefine proxy or cookie settings for this module. The existing application configuration remains authoritative.

---

# 5. Database ownership and separation

Use the existing Telephony Toolbox application database for all module configuration and application-owned state. Configure the AudioCodes SDR/CDR database as a distinct external source connection. The module must not introduce a second application database.

## 5.1 AudioCodes source database

The AudioCodes PostgreSQL 17 source database contains:

```text
public.sdr
public.cdr
```

It must be accessed using a dedicated read-only PostgreSQL account, independently of the Telephony Toolbox application database.

The source database must be treated as completely immutable.

The application must not:

- insert records;
- update records;
- delete records;
- run migrations against the source database;
- create Django migration tables in the source database;
- create or modify source sequences;
- create indexes automatically;
- add constraints;
- modify permissions;
- lock source rows deliberately;
- use `SELECT FOR UPDATE`;
- perform schema-management operations.

The source models must be configured as unmanaged Django models:

```python
class Meta:
    managed = False
```

A Django database router must prevent migrations and write operations from being directed to the source connection.

The supplied source account must also be restricted at the PostgreSQL layer to `SELECT` access only. Application-level protections are not a substitute for database permissions. Every configured source option, including a primary rather than a replica, remains read-only.

## 5.2 Telephony Toolbox application database

Use the existing Telephony Toolbox application database and configured database connection for:

- Django sessions;
- all AudioCodes module configuration and application-owned state, including any persisted display preferences;
- module-owned Django migration state, if application tables are required.

Do not create a dedicated CDR Manager application database or copy/replicate SDR or CDR records into the Telephony Toolbox database. Manage module settings through an App Admin-only settings page in the existing application (not Django Admin). Store the source connection profile and its credential in the Telephony Toolbox database, encrypting the credential at rest with an encryption key kept outside that database in protected deployment configuration. Never store or return plaintext credentials.

## 5.3 Source connection selection

Both the primary and a read replica are available.

The default source connection should be the read replica when configured.

The primary may be configured as an explicit alternative source, but the module must not silently switch sources. Any configured source remains read-only, and the active source selection must be visible to App Admins.

The database also performs live ingestion and replication. Queries must therefore be conservative, bounded and index-conscious.

---

# 6. Existing source schema

The application must map the source tables exactly as they currently exist.

## 6.1 SDR fields

```text
id
recordtype
sessionid
setuptime
connecttime
releasetime
timetoconnect
callduration
sourceip
destinationip
ingressipgroup
egressipgroup
ingressani
ingressdnis
egressani
egressdnis
ingresscallid
egresscallid
ingressremotertpip
ingressremotertpport
egressremotertpip
egressremotertpport
globalsessionid
ingressterminationreason
egressterminationreason
ingresssipterminationreason
egresssipterminationreason
issuccess
```

The SDR primary key is `id`.

## 6.2 CDR fields

```text
id
cdrtype
reporttype
callid
globalsessionid
sessionid
legid
callerdisplayid
sourceusernamebeforemanip
sourceusername
sourcetags
calleedisplayid
destinationusernamebeforemanip
destinationusername
destinationtags
sipinterfacename
ipgroupname
proxysetname
remoteip
remoteport
remotertpip
remotertpport
codertype
callorig
terminationside
cdrtrigger
alertingtime
callduration
wascallstarted
callsuccess
setuptime
connecttime
releasetime
terminationreason
terminationreasoncategory
sipterminationreason
sipterminationdescription
terminationsideradius
terminationsideyesno
terminationreasonvalue
localjitter
localpacketloss
localroundtripdelay
remotejitter
remotepacketloss
remoteroundtripdelay
varcalluserdefined1
varcalluserdefined2
varcalluserdefined3
varcalluserdefined4
varcalluserdefined5
```

The CDR primary key is `id`.

The implementation must not rename these fields in the source models. User-friendly API labels or frontend labels may be added separately.

---

# 7. Dataset scale

The design must account for approximately:

```text
SDR rows: 5,932,734
CDR rows: 1,227,223,976
```

Approximate ongoing growth is:

```text
SDR: 1,000 rows per day
CDR: 2,500 rows per day
```

Data retention is indefinite.

The oldest current records date from April 2023.

The application must not:

- load unbounded result sets;
- perform client-side result filtering;
- fetch all matching rows before pagination;
- scan the CDR table to populate general lookup controls;
- calculate charts in the browser from detailed result rows;
- fetch associated CDRs until an SDR details page is opened.

A 60-second PostgreSQL statement timeout must be applied to source queries.

---

# 8. Authentication and authorization

## 8.1 Existing Telephony Toolbox authentication

Do not implement a module-specific login, identity-provider integration, LDAP search/bind flow, user store, break-glass account, or session mechanism. Users authenticate through the existing Telephony Toolbox login and configured provider (Entra or LDAP, with the existing local fallback). The module consumes the current authenticated Django session and canonical Telephony Toolbox user identity. Do not request credentials again or store authentication credentials.

## 8.2 Identity-provider configuration

All LDAP, Entra and local-fallback configuration belongs to the existing Telephony Toolbox deployment configuration and authentication implementation. Do not add, duplicate, override or weaken provider settings for this module. In particular, do not add a module-specific LDAP group filter or disable certificate validation.

## 8.3 App Admin-only authorization

Every page, API endpoint, lookup, search, detail, statistics result and module-setting operation is restricted to the existing Telephony Toolbox `App Admin` role. Use the project’s existing permission implementation (such as `IsAppAdmin`) on the backend; hiding frontend navigation is supplementary and is not authorization. Standard Users and unauthenticated users must not access AudioCodes data. Do not add a CDR-specific role or group.

## 8.4 Existing local fallback

Use only the local fallback already supported by Telephony Toolbox. Do not create a separate break-glass identity, account lifecycle, password command or alternate authorization rule for this module. App Admin status is determined by the existing user role.

## 8.5 Sessions and CSRF

Use the existing Django cookie-based session authentication and CSRF protection. Do not introduce JWTs, a second session cookie, a module-specific cookie path, or changes to shared session lifetime and security settings. All module write requests (including preference or configuration updates) must follow existing CSRF handling. Do not duplicate authentication audit events; use the existing application audit and logging facilities where applicable.

---

# 9. Source data interpretation

## 9.1 SDR meaning

An SDR represents the entire AudioCodes session and is the primary entity in the application.

One SDR counts as one call or session for search and statistical purposes.

## 9.2 CDR meaning

A CDR represents an individual call leg.

An SBC can terminate an incoming SIP session and originate a new outgoing SIP session. These are separate legs and therefore separate CDR records.

An SDR can have:

- no associated CDRs;
- one associated CDR;
- two associated CDRs;
- more than two associated CDRs.

All associated CDRs must be retained in the display, including failed, cancelled, forked and alternate-route records.

## 9.3 CDR direction

Classify CDR direction using `callorig`:

```text
RMT = inbound or remotely originated
LCL = outbound or locally originated
Other or blank = unknown
```

The frontend must show the raw `callorig` value as well as the friendly classification.

Do not infer direction only from `legid`, IP group or CDR display order.

## 9.4 Associated CDR ordering

Associated CDRs must be ordered by:

```text
legid ASC NULLS LAST,
id ASC
```

The `id` field is the deterministic tie-breaker.

---

# 10. SDR-to-CDR correlation

## 10.1 Primary rule

The primary association is:

```sql
cdr.sessionid = sdr.sessionid
```

The details API must:

1. retrieve the SDR by SDR primary key `id`;
2. read its `sessionid`;
3. query CDR rows with an equal `sessionid`;
4. order the CDRs by `legid`, then `id`;
5. return every matching CDR.

Use a parameterised query or ORM filtering.

## 10.2 Global Session ID

Do not use `globalsessionid` as the sole correlation key.

AudioCodes describes the Global Session ID as identifying a call session and remaining consistent when that call traverses multiple enabled devices. The same Global Session ID may consequently appear in records associated with multiple devices. It is also not included in CDRs by default unless CDR customisation enables it.

Use `globalsessionid` for:

- display;
- diagnostic comparison;
- anomaly detection;
- future cross-device investigation.

Do not automatically attach a CDR to an SDR using only a matching Global Session ID.

## 10.3 Call-ID comparison

Display:

- SDR `ingresscallid`;
- SDR `egresscallid`;
- each CDR `callid`.

Use these values for troubleshooting and anomaly indicators, but do not use Call-ID as the primary join in the first release.

## 10.4 Correlation anomalies

The details API must calculate anomaly flags without modifying source records.

Detect at least:

- SDR has a blank `sessionid`;
- SDR has no matching CDRs;
- duplicate `legid` values among associated CDRs;
- CDR with blank `legid`;
- matching CDR has a different non-blank `globalsessionid`;
- matching CDR has a blank `globalsessionid` while the SDR has one;
- associated CDR has an unknown `callorig`;
- no CDR `callid` corresponds to either SDR ingress or egress Call-ID.

These are diagnostic warnings, not reasons to exclude a CDR.

The details page must visibly distinguish:

- no anomaly;
- informational anomaly;
- warning anomaly.

Do not invent or display an authoritative "correlation confidence score".

---

# 11. Time and duration handling

## 11.1 Duration units

The following interval values use hundredths of a second:

- SDR `callduration`;
- SDR `timetoconnect`;
- CDR `callduration`;
- CDR `alertingtime`.

For example:

```text
37501 hundredths = 375.01 seconds = 00:06:15.01
```

The API must return the original source value.

The frontend is responsible for formatting the value.

## 11.2 Duration display preference

Users can select:

- decimal seconds;
- `HH:MM:SS.ff`.

Examples:

```text
375.01 seconds
00:06:15.01
```

The selected format must be stored as a per-user preference in the Telephony Toolbox application database and used consistently in:

- search results;
- SDR detail;
- CDR cards;
- statistics;
- tooltips.

Do not persist module preferences in browser-local storage or another database. Persist the duration-format preference per Telephony Toolbox user. Preferences must never be written to the AudioCodes source database.

## 11.3 Null and invalid durations

Although SDR `callduration` is text, expected populated values are numeric.

Frontend formatting must safely handle:

- null;
- blank string;
- unexpected non-numeric values;
- zero;
- very large values.

For null or blank values, display a blank value.

For an unexpected non-numeric value, show the original value and mark it as unformatted rather than failing the page.

## 11.4 Timezone

Display all timestamps in:

```text
Australia/Sydney
```

The implementation must correctly handle Australian daylight-saving transitions.

Timestamps must retain millisecond precision where present.

Suggested display format:

```text
DD/MM/YYYY HH:mm:ss.SSS z
```

## 11.5 Search timestamp

SDR date filtering is based exclusively on:

```text
sdr.setuptime
```

Do not substitute `connecttime` in the database search predicate.

Historical records with a blank `setuptime` will therefore not match a setup-time range search.

## 11.6 Display fallback

For search result and detail display:

1. use `setuptime` when present;
2. otherwise use `connecttime`;
3. visibly identify when `connecttime` is being displayed as the fallback.

Do not silently label `connecttime` as setup time.

Records without `setuptime` are understood to be historical data affected by a previous collection fault.

---

# 12. Telephony Toolbox navigation

Add the module as an App Admin-only destination within the existing Telephony Toolbox navigation and shared application shell. Use these frontend routes:

```text
/admin/cdr
/admin/cdr/sessions/:id
/admin/cdr/statistics
/admin/cdr/settings
```

Provide the specified search, session detail, statistics and settings views using the shared route/layout conventions. Do not add a module login/logout screen; unauthenticated users use the existing login flow. Every API request independently enforces authentication and App Admin authorization; frontend route protection is not sufficient.

---

# 13. SDR search

## 13.1 General behaviour

SDR search is the primary application function.

On initial entry, the search defaults to the current calendar day:

```text
00:00:00 Australia/Sydney through the current time
```

Every search requires a bounded setup-time range.

The maximum permitted range is 12 months.

Validate the range in both:

- frontend;
- backend.

The backend is authoritative.

## 13.2 Search filters

Support the following filters.

### Setup time

- start date and time;
- end date and time;
- required;
- maximum span of 12 months.

### Ingress IP group

- database-populated;
- multi-select;
- exact matching.

### Egress IP group

- database-populated;
- multi-select;
- exact matching.

### ANI

Search both:

```text
ingressani
egressani
```

Supported matching modes:

- exact;
- starts with;
- ends with;
- contains.

### DNIS

Search both:

```text
ingressdnis
egressdnis
```

Supported matching modes:

- exact;
- starts with;
- ends with;
- contains.

### Call-ID

Search both:

```text
ingresscallid
egresscallid
```

Use the same four matching modes unless the implementation identifies a material performance concern. Exact matching should be the default.

### Status

Support:

- all;
- successful;
- unsuccessful;
- unknown or null.

Map this to SDR `issuccess`.

### Termination reason

Search:

```text
ingressterminationreason
egressterminationreason
ingresssipterminationreason
egresssipterminationreason
```

Support exact selection where distinct configured values are available, plus text matching.

## 13.3 Boolean logic

Different filters are combined with `AND`.

Directional fields inside a single logical filter are combined with `OR`.

Example:

```sql
setuptime >= :start_time
AND setuptime < :end_time
AND (
    ingressani LIKE :ani_pattern
    OR egressani LIKE :ani_pattern
)
AND ingressipgroup = ANY(:ingress_groups)
AND issuccess = FALSE
```

IP-group selections inside the same multi-select use `OR`/`IN` semantics.

## 13.4 Unsupported first-release filters

The primary search does not need dedicated filters for:

- source IP;
- destination IP;
- RTP IP;
- SDR session ID;
- Global Session ID;
- database ID.

These values remain visible on the details page.

Independent CDR search is Phase 2 and must not be implemented as part of this release.

## 13.5 Search state

When a user opens an SDR and then returns to search, retain:

- filters;
- match modes;
- sort column;
- sort direction;
- current page;
- page size.

This may be implemented using frontend state plus route query parameters.

The search should be shareable through a URL where practical, but credentials and sensitive session information must never be placed in the URL.

## 13.6 Search actions

Provide:

- Search;
- Clear filters;
- Reset to today;
- previous page;
- next page;
- first page;
- last page where supported by the count;
- sortable column headings.

Do not provide any export function.

---

# 14. IP-group lookup values

Ingress and egress IP-group controls must use cached values.

The backend should obtain distinct values independently for:

```text
sdr.ingressipgroup
sdr.egressipgroup
```

Requirements:

- exclude null and blank values;
- sort alphabetically;
- cache results;
- make cache lifetime configurable;
- provide a graceful error if values cannot be refreshed;
- do not query the CDR table for these controls.

A reasonable initial cache lifetime should be supplied as a configurable default, not hard-coded into business logic.

---

# 15. Search result table

## 15.1 Default columns

Display:

1. setup or effective start time;
2. ingress ANI;
3. ingress DNIS;
4. egress ANI;
5. egress DNIS;
6. ingress IP group;
7. egress IP group;
8. call duration;
9. success status;
10. termination summary;
11. View action.

## 15.2 Effective start time

When `setuptime` is null and `connecttime` is used, add a visible indicator or tooltip such as:

```text
Connect time shown because setup time is unavailable.
```

## 15.3 Termination summary

Construct the displayed summary from existing SDR fields only.

Preferred display:

- ingress termination reason;
- egress termination reason;
- ingress SIP termination reason;
- egress SIP termination reason.

Avoid repeating identical values unnecessarily, but all values must remain accessible from the details page.

Do not invent a normalised failure reason unless explicitly mapped in configuration.

## 15.4 Success highlighting

Unsuccessful calls must be visibly highlighted.

Use accessible styling:

- icon;
- text label;
- colour.

Do not rely on colour alone.

Null success status must be distinct from both successful and unsuccessful.

## 15.5 Pagination

All pagination is server-side.

Default page size:

```text
100
```

Provide sensible selectable page sizes around that default, provided every request remains bounded.

## 15.6 Sorting

All sorting is server-side.

Sort only by an allow-list of supported fields.

Default sort:

```text
setuptime DESC,
id DESC
```

Never accept an arbitrary database column or SQL fragment directly from the client.

## 15.7 Exact count

Calculate and display the exact total number of matches.

The count and row retrieval may be separate queries.

Both queries must:

- use the same validated filters;
- honour the 60-second statement timeout;
- return a controlled timeout error if unable to complete.

Do not degrade silently to an estimated count.

## 15.8 No export

Do not implement:

- CSV export;
- Excel export;
- PDF export;
- bulk download;
- API export endpoint.

The permitted export-record limit is therefore zero.

---

# 16. SDR details page

The View action opens the module’s dedicated session-detail route within the existing Telephony Toolbox SPA:

```text
/admin/cdr/sessions/:id
```

Retrieve the SDR using its numeric primary key.

The page must contain the following sections.

## 16.1 Call overview

Show:

- success;
- displayed start time;
- setup time;
- connect time;
- release time;
- time to connect;
- call duration;
- ingress IP group;
- egress IP group;
- ingress ANI;
- ingress DNIS;
- egress ANI;
- egress DNIS.

## 16.2 Visual call path

Display a clear visual path such as:

```text
Source
  ↓
Ingress IP Group
  ↓
AudioCodes SBC Session
  ↓
Egress IP Group
  ↓
Destination
```

Include:

- source IP;
- destination IP;
- ingress IP group;
- egress IP group;
- ingress ANI and DNIS;
- egress ANI and DNIS.

The visual must make number manipulation obvious by showing ingress and egress values separately.

Do not imply that a value changed where the source values are blank or identical.

## 16.3 Timing

Show:

- setup time;
- connect time;
- release time;
- time to connect;
- call duration;
- raw duration values;
- selected formatted duration values.

## 16.4 Termination

Show:

- ingress termination reason;
- egress termination reason;
- ingress SIP termination reason;
- egress SIP termination reason;
- success status.

Contextual help must explain fields using the version-appropriate AudioCodes documentation where documentation is available.

## 16.5 Media and RTP

Show:

- ingress remote RTP IP;
- ingress remote RTP port;
- egress remote RTP IP;
- egress remote RTP port;
- CDR media-quality fields on their respective CDR cards.

## 16.6 Identifiers

Show:

- SDR database ID;
- record type;
- session ID;
- Global Session ID;
- ingress Call-ID;
- egress Call-ID.

Provide copy-to-clipboard controls for identifiers and telephone-number fields.

## 16.7 All SDR fields

Every SDR field must be shown somewhere on the page.

There is no separate raw-view mode.

Fields that have not been assigned a specialised section should appear under an "Additional SDR fields" section.

Null fields must remain present and display a blank value.

Do not:

- omit null-valued fields;
- display the literal string `"null"`;
- replace null with fabricated values;
- hide fields merely because they are uncommon.

---

# 17. CDR leg cards

Associated CDRs must be displayed as expandable cards.

## 17.1 Card header

Each card header should show:

- leg ID;
- direction classification;
- raw `callorig`;
- IP group;
- source number;
- destination number;
- success status;
- termination reason;
- duration.

## 17.2 Expanded details

The expanded card must expose every CDR field grouped into logical sections:

### Identity

- ID;
- CDR type;
- report type;
- Call-ID;
- session ID;
- Global Session ID;
- leg ID.

### Calling and called party

- caller display ID;
- source username before manipulation;
- source username;
- source tags;
- callee display ID;
- destination username before manipulation;
- destination username;
- destination tags.

### Routing

- SIP interface name;
- IP group name;
- proxy set name;
- remote signalling IP;
- remote signalling port;
- call origin;
- termination side.

### Media

- remote RTP IP;
- remote RTP port;
- coder type;
- local jitter;
- local packet loss;
- local round-trip delay;
- remote jitter;
- remote packet loss;
- remote round-trip delay.

### Timing and outcome

- CDR trigger;
- alerting time;
- call duration;
- call started;
- call success;
- setup time;
- connect time;
- release time.

### Termination

- termination reason;
- termination reason category;
- SIP termination reason;
- SIP termination description;
- termination-side RADIUS value;
- termination-side yes/no;
- termination reason value.

### User-defined fields

- `varcalluserdefined1`;
- `varcalluserdefined2`;
- `varcalluserdefined3`;
- `varcalluserdefined4`;
- `varcalluserdefined5`.

Null values remain visible as blank values.

## 17.3 Tag parsing

Parse `sourcetags` and `destinationtags` as semicolon-separated key/value pairs where possible.

Example:

```text
ROUTE=GENESYS_01;OWNER=NBNCO;ALLOWEDCLI=GENESYS
```

Display as:

```text
ROUTE        GENESYS_01
OWNER        NBNCO
ALLOWEDCLI   GENESYS
```

Also display or otherwise preserve access to the original unmodified string.

Parsing must be defensive:

- preserve entries without `=`;
- split each pair only at the first `=`;
- preserve unknown keys;
- do not convert key names;
- do not discard malformed content.

## 17.4 User-defined labels

Friendly labels for `varcalluserdefined1` through `varcalluserdefined5` must be configurable.

Example configuration:

```yaml
cdr_user_defined_fields:
  varcalluserdefined1:
    label: "User Defined 1"
    description: ""
  varcalluserdefined2:
    label: "User Defined 2"
    description: ""
  varcalluserdefined3:
    label: "User Defined 3"
    description: ""
  varcalluserdefined4:
    label: "User Defined 4"
    description: ""
  varcalluserdefined5:
    label: "User Defined 5"
    description: ""
```

Undefined fields retain a sensible default label.

---

# 18. Media-quality thresholds

Colour-code:

- local jitter;
- remote jitter;
- local packet loss;
- remote packet loss;
- local round-trip delay;
- remote round-trip delay.

Warning and critical thresholds must be configurable independently for each metric.

Example structure:

```yaml
media_quality:
  local_jitter:
    warning: null
    critical: null
    unit: ""
  remote_jitter:
    warning: null
    critical: null
    unit: ""
  local_packet_loss:
    warning: null
    critical: null
    unit: ""
  remote_packet_loss:
    warning: null
    critical: null
    unit: ""
  local_round_trip_delay:
    warning: null
    critical: null
    unit: ""
  remote_round_trip_delay:
    warning: null
    critical: null
    unit: ""
```

Until valid thresholds and units are configured:

- show the raw value;
- do not assign warning or critical status;
- do not assume units.

Use accessible status indicators in addition to colour.

---

# 19. AudioCodes contextual help

The source data originates from AudioCodes version 7.4 JSON messages.

Configured field names have not been customised.

The application must provide contextual help for:

- SDR fields;
- CDR fields;
- call direction;
- termination reasons;
- SIP termination reasons;
- timing values;
- media-quality fields.

Requirements:

- keep help content separate from source data;
- allow help text to be maintained through configuration or static application resources;
- identify the documentation version as AudioCodes 7.4;
- do not alter the source data based on documentation;
- do not claim a termination explanation where no documented mapping has been configured.

AudioCodes permits REST CDR reporting in JSON and allows CDR fields or names to be customised. Although this installation has not customised the field names, the implementation should keep field descriptions separate from model definitions.

---

# 20. Statistics

## 20.1 General behaviour

The statistics view operates on SDR records only.

One SDR equals one call/session.

Calls are bucketed using:

```text
sdr.setuptime
```

Records with null setup time are excluded from setup-time statistics.

The statistics view must reuse the same relevant filters as SDR search.

## 20.2 Preset ranges

Provide:

- last 24 hours;
- last 48 hours;
- last 7 days;
- last month;
- custom range.

"Last month" must mean the previous complete calendar month in `Australia/Sydney`, not merely the previous 30 days.

Custom ranges must remain subject to the 12-month maximum.

## 20.3 Bucket selection

Support hourly and daily buckets.

Automatically select an appropriate bucket:

- hourly for short ranges;
- daily for longer ranges.

The exact switching threshold must be configurable or clearly defined in the implementation.

The interface must show the selected bucket size.

Zero-call intervals must appear with zero values.

All interval boundaries must be evaluated using `Australia/Sydney`.

## 20.4 Required statistics

Provide:

1. total calls per interval;
2. successful calls per interval;
3. unsuccessful calls per interval;
4. success rate;
5. average call duration;
6. average time to connect;
7. calls grouped by ingress IP group;
8. calls grouped by egress IP group;
9. top termination reasons.

Null `issuccess` values must not be silently counted as successful or unsuccessful. They may be displayed as unknown.

## 20.5 Duration aggregation

Because SDR `callduration` is stored as text, aggregation must only cast values that are valid numeric strings.

Invalid or blank values:

- remain visible on individual records;
- are excluded from numeric average calculations;
- must not cause the query to fail.

Statistics API responses must include a count of records excluded from an average due to blank or invalid duration data.

## 20.6 Charts

Use Apache ECharts.

Charts must be:

- responsive;
- accessible;
- readable in current Microsoft Edge;
- interactive;
- able to display tooltips;
- capable of drill-down.

Recommended charts:

- stacked or grouped time-series chart for successful and unsuccessful calls;
- line or bar chart for total calls;
- success-rate line;
- bar chart for ingress IP groups;
- bar chart for egress IP groups;
- horizontal bar chart for top termination reasons;
- summary cards for total calls, success rate, average duration and average time to connect.

## 20.7 Drill-down

Selecting a time bucket must navigate to the SDR search page with:

- start time set to the selected bucket start;
- end time set to the selected bucket end;
- applicable statistics filters retained.

Do not navigate using only a human-readable chart label. Use exact ISO timestamps or structured route state.

---

# 21. API requirements

## 21.1 API style

Use Django REST Framework.

JSON is the API representation.

Formal public OpenAPI/Swagger exposure is not required.

The API still requires:

- consistent serializers;
- validation;
- controlled errors;
- predictable pagination;
- stable response structures.

## 21.2 Suggested endpoint operations

Add the following operations under the existing Telephony Toolbox API prefix at `/api/admin/cdr/`:

```text
GET  /api/admin/cdr/sdr/
GET  /api/admin/cdr/sdr/{id}/

GET  /api/admin/cdr/lookups/ingress-ip-groups/
GET  /api/admin/cdr/lookups/egress-ip-groups/
GET  /api/admin/cdr/lookups/termination-reasons/

GET  /api/admin/cdr/statistics/summary/
GET  /api/admin/cdr/statistics/timeseries/
GET  /api/admin/cdr/statistics/ip-groups/
GET  /api/admin/cdr/statistics/termination-reasons/

GET  /api/admin/cdr/config/display/
GET  /api/admin/cdr/preferences/
PUT  /api/admin/cdr/preferences/
GET  /api/admin/cdr/settings/
PUT  /api/admin/cdr/settings/
```

Do not add module-specific login, logout, session, readiness or health endpoints. Use the existing Telephony Toolbox authentication, user/session, and health APIs. All listed operations are App Admin-only. Settings updates must use existing CSRF handling, encrypt source credentials before persistence, never include plaintext credentials in responses or logs, and record the configuration change through the existing audit system. Do not audit CDR searches or individual record views.

The implementing LLM may consolidate statistics endpoints if the resulting query behaviour and response size remain efficient.

## 21.3 SDR list response

Return:

- paginated SDR summaries;
- exact total result count;
- current page;
- page size;
- sort definition;
- applied filter summary.

Do not include associated CDRs in the list response.

## 21.4 SDR detail response

Return:

- complete SDR source fields;
- associated CDR records;
- derived direction labels;
- parsed tags;
- correlation anomalies;
- display-help metadata where appropriate.

Derived values must be clearly separated from raw source fields.

Suggested structure:

```json
{
  "sdr": {
    "raw": {},
    "display": {}
  },
  "cdrs": [
    {
      "raw": {},
      "display": {},
      "parsed_tags": {}
    }
  ],
  "anomalies": []
}
```

Do not overwrite raw fields with formatted values.

## 21.5 Validation

The backend must validate:

- required start and end times;
- start precedes end;
- range is no greater than 12 months;
- allowable matching modes;
- allowable status values;
- page size limits;
- sort fields;
- sort direction;
- SDR numeric ID;
- multi-select size limits;
- timestamp timezone handling.

## 21.6 Error responses

Provide controlled responses for:

- unauthenticated access;
- unauthorised access;
- invalid filters;
- range too large;
- source database timeout;
- source database unavailable;
- SDR not found;
- application configuration error.

Do not return:

- SQL;
- stack traces;
- database hostnames;
- LDAP bind details;
- passwords;
- internal filesystem paths.

---

# 22. Query and performance requirements

## 22.1 Search query design

The search query must begin with the bounded `setuptime` predicate so PostgreSQL can use the existing descending setup-time index.

Use parameterised values throughout.

Avoid applying functions to `setuptime` in the `WHERE` predicate.

Prefer:

```sql
setuptime >= :start_utc
AND setuptime < :end_utc
```

Do not use:

```sql
DATE(setuptime) = ...
```

Convert Australia/Sydney boundaries to timezone-aware timestamps before query execution.

## 22.2 Number matching

Exact and prefix searches may use the existing ANI/DNIS indexes more effectively than leading-wildcard searches.

Contains and ends-with searches can be expensive. They must still be supported, but:

- always require the bounded date range;
- remain subject to the 60-second statement timeout;
- provide a clear timeout message;
- never retry automatically with a broader query.

## 22.3 CDR retrieval

Retrieve CDRs only for one opened SDR:

```sql
WHERE sessionid = :sessionid
ORDER BY legid ASC NULLS LAST, id ASC
```

Use the existing `cdr.sessionid` index.

Do not query all CDRs for the result page.

## 22.4 Caching

Caching is permitted for:

- ingress IP groups;
- egress IP groups;
- termination-reason lookup values;
- statistics;
- field-help metadata;
- display configuration.

Caching must not cause users to see incorrect individual SDR or CDR details.

Individual session details should be queried from the source when opened unless a short and explicitly documented cache is used.

## 22.5 Database index recommendations

Do not create source indexes automatically.

Provide a separate index recommendation document containing:

- proposed SQL;
- reason for each index;
- affected query;
- expected benefit;
- storage and write impact;
- suggested validation using `EXPLAIN (ANALYSE, BUFFERS)`;
- rollback SQL.

Recommendations must consider the source table size, especially the 1.2-billion-row CDR table.

Do not recommend an index merely because a field is searchable. Evaluate whether the bounded setup-time predicate and expected selectivity justify it.

---

# 23. Health and source-availability reporting

Use the existing Telephony Toolbox health/status API and admin health view. Report AudioCodes source-database availability using a lightweight read-only query, without exposing credentials, server addresses, database names or exception traces. Do not add a module-specific readiness endpoint or repeat LDAP/provider health checks. If the AudioCodes source is unavailable, mark this module unavailable while preserving normal access to the rest of Telephony Toolbox.

The existing health/status response should expose a concise AudioCodes-source status consistent with the current Telephony Toolbox health response format; do not define a competing response schema here.

---

# 24. Logging

Use the existing Telephony Toolbox logging configuration, format, correlation identifiers, log rotation and file permissions. Do not create separate CDR-module log files or an authentication subsystem log. Never log credentials, session cookies or full database connection strings; avoid ANI/DNIS in routine request logs.

---

# 25. Configuration

The existing Telephony Toolbox deployment configuration remains authoritative for Django, application-database connectivity, authentication providers, session/CSRF behavior, logging and shared deployment settings. Do not duplicate those settings for this module.

Persist all AudioCodes module configuration and application-owned state in the existing Telephony Toolbox application database, including the selected source profile, source selection, query limits, cache lifetimes, statistics bucket settings, field labels/help, media-quality units/thresholds, per-user display preferences, and the encrypted source-connection credential. Maintain these settings through an App Admin-only settings page in the existing application, not Django Admin. Keep the encryption key outside the database in protected deployment configuration. The AudioCodes database is a distinct read-only source, not a place to store module configuration. Never store or return plaintext secrets or commit secrets to source control.

Configuration errors affecting authorization, source immutability or credential protection must fail closed. Follow the existing application database migration conventions; do not introduce another configuration database.

---

# 26. Frontend usability

## 26.1 General design

The interface should be operationally focused, concise and suitable for engineers troubleshooting calls.

Use:

- clear section headings;
- compact tables;
- fixed-width presentation for identifiers where useful;
- copy buttons;
- meaningful success and failure indicators;
- responsive layout;
- accessible keyboard navigation;
- colour plus icon/text status indicators.

## 26.2 Loading behaviour

Display:

- search progress;
- statistics loading;
- session-detail loading;
- controlled timeout errors.

Prevent accidental duplicate searches while an identical request is active.

A new search may cancel an obsolete frontend HTTP request, but the backend must still rely on statement timeout and connection cleanup.

## 26.3 Empty states

Provide meaningful messages for:

- no search results;
- SDR has no associated CDRs;
- statistics range has no calls;
- IP-group lookups unavailable;
- missing setup time;
- null success status;
- source database unavailable.

## 26.4 Browser support

Primary supported browser:

```text
Current enterprise-supported Microsoft Edge
```

The application should also avoid browser-specific behaviour that unnecessarily prevents operation in a current Chromium-based browser.

---

# 27. Security requirements

The implementation must:

- use server-side Django sessions;
- use secure and HTTP-only cookies;
- use CSRF protection;
- enforce authentication and existing App Admin permission on every data endpoint;
- enforce the 12-month maximum server-side;
- use parameterised database access;
- use a read-only source database account;
- prevent migration operations on the source;
- validate sort and filter fields against allow-lists;
- avoid exposing internal exceptions;
- avoid secrets in logs;
- avoid credentials in frontend code;
- use a non-root operating-system service account;
- include appropriate response security headers;
- deny framing unless the deployment specifically requires it;
- avoid caching authenticated call data in shared intermediary caches.

Source ANI and DNIS values may be displayed in full to authorized App Admins.

Record module configuration changes in the existing audit system. Do not record searches or individual record views, and do not create a parallel audit subsystem.

---

# 28. Prohibited functionality

The first release must not implement:

- writing to `cdr`;
- writing to `sdr`;
- deletion of source records;
- independent CDR search;
- CSV export;
- Excel export;
- bulk export;
- module-specific login, LDAP, Entra or local-authentication flows;
- module-specific roles or groups;
- a separate application database;
- copied or replicated SDR/CDR records;
- source-schema migrations;
- automatic source-index creation;
- raw JSON display, because original JSON is unavailable;
- synthetic production datasets or writes to the source database;
- public Swagger/OpenAPI UI.

Module verification must follow the existing Telephony Toolbox testing and validation conventions, including backend tests and applicable frontend lint/build checks. Do not carry over the standalone specification’s prohibition on automated tests.

---

# 29. Deployment deliverables

Implement this as a feature within the existing Telephony Toolbox source tree and conventions. Module deliverables are:

1. unmanaged SDR/CDR source mappings and guarded read-only source connection;
2. any required module configuration/state models and application-database migrations;
3. source-database router/guards that prevent writes and migrations;
4. authenticated App Admin-only API operations;
5. integrated search, session details, statistics and settings views;
6. source-availability reporting through existing health/status facilities;
7. integration and operator documentation in the existing documentation structure;
8. backend tests and applicable frontend validation following existing project conventions.

Do not generate a separate project, installation stack, frontend build, dependency environment, service unit, or Nginx deployment fragment.

---

# 30. Shared deployment requirements

Deploy and operate the module through the existing Telephony Toolbox Django/Gunicorn service, systemd unit, frontend build, environment configuration and application release process. Do not add a `cdrmanager.service`, separate Python environment, installation root, or service-specific operational lifecycle.

---

# 31. Shared reverse-proxy requirements

Use the existing Telephony Toolbox Nginx and F5 reverse-proxy path. Do not generate a module-specific Nginx fragment, route mount, TLS configuration, or cache policy. Authenticated module API responses must follow the existing no-shared-cache policy.

---

# 32. Documentation requirements

Document the module in the existing Telephony Toolbox development, configuration, API, architecture, deployment and operations documentation as appropriate. Cover the separate read-only source connection, application-database settings/state, source protections, query/performance limits, App Admin access, troubleshooting and source availability. Do not create standalone installation, service, authentication, Nginx or upgrade guides. The AudioCodes source database must never form part of the Telephony Toolbox application migration or backup/restore workflow except where its own DBA processes require it.

---

# 33. Acceptance criteria

The implementation is acceptable when all of the following are true.

## 33.1 Authentication

- The existing Telephony Toolbox login and configured provider authenticate users; the module has no separate login flow.
- An authenticated App Admin can access module pages and APIs.
- Standard Users and unauthenticated users are denied by backend permission checks.
- Existing session cookies and CSRF protection are reused without module-specific changes.
- No duplicate user, LDAP, Entra, local-fallback or session implementation exists.

## 33.2 Source protection

- The source models are unmanaged.
- Source database credentials are read-only.
- Django migrations do not run against the source database.
- The application can operate without source write permission.
- No source table or index is created or altered.
- All module configuration and application-owned state use the existing Telephony Toolbox application database.
- The external SDR/CDR source remains separately configured and contains no module-owned configuration or state.
- No SDR or CDR records are copied into the Telephony Toolbox application database.

## 33.3 Search

- The default range is today from midnight to now in Australia/Sydney.
- Searches without valid bounds are rejected.
- Searches longer than 12 months are rejected.
- ANI and DNIS support all four match modes.
- Ingress and egress IP groups support multi-select controls.
- Filters use the required AND/OR semantics.
- Results are server-side paginated.
- Default page size is 100.
- Exact total count is returned.
- No export control or export endpoint exists.

## 33.4 Session details

- An SDR opens on a dedicated page.
- Every SDR field is visible.
- Null fields remain visible as blank.
- Associated CDRs are retrieved by matching `sessionid`.
- CDRs are ordered by `legid`, then `id`.
- Every CDR field is accessible.
- `RMT` and `LCL` are classified correctly.
- More than two CDR legs are supported.
- Failed and cancelled legs are not discarded.
- Correlation anomalies are shown.
- Tags are parsed while preserving their original value.

## 33.5 Time and duration

- Setup-time filtering uses `sdr.setuptime`.
- Display falls back to `connecttime` when setup time is blank.
- The fallback is visibly identified.
- Timestamps display in Australia/Sydney.
- Milliseconds are preserved.
- Duration can be displayed as decimal seconds or `HH:MM:SS.ff`.
- Raw API duration values are not replaced by formatted values.

## 33.6 Statistics

- One SDR counts as one call.
- Calls are bucketed using setup time.
- Zero-call intervals are displayed.
- All required metrics are available.
- Last 24 hours, last 48 hours, last 7 days, last month and custom ranges are supported.
- Longer ranges use daily aggregation.
- Chart selection drills into the matching SDR search.
- Invalid text durations do not break averages.

## 33.7 Telephony Toolbox integration

- The module is available from the existing Telephony Toolbox SPA and API host.
- Frontend pages use `/admin/cdr` and its child routes; APIs use `/api/admin/cdr/`.
- It follows the shared frontend, API, logging, health/status and deployment conventions.
- No standalone URL mount, service, Nginx fragment, authentication flow, or application database is introduced.
- AudioCodes source availability is reported through existing health/status facilities.
- Microsoft Edge can use all primary functions.

## 33.8 Settings and audit

- Module settings are maintained through an App Admin-only page at `/admin/cdr/settings`.
- Module configuration and state, including the source profile and encrypted credential, are persisted in the Telephony Toolbox application database.
- The encryption key is outside the application database in protected deployment configuration; plaintext credentials are never stored, returned or logged.
- Configuration changes are recorded in the existing audit system.
- Searches and individual SDR/CDR views are not recorded in the audit system.
- Backend tests and applicable frontend lint/build checks follow existing repository conventions.

---

# 34. Implementation priorities

Implement in this order within the existing Telephony Toolbox:

1. configure the separate source connection and enforce source-write/migration protections;
2. map unmanaged SDR/CDR models;
3. add module configuration/state to the existing application database;
4. implement App Admin-only APIs using existing authentication and permission conventions;
5. implement SDR search with exact count and server-side pagination;
6. add IP-group lookup caching;
7. integrate search into the selected `/admin/cdr` route and shared Quasar shell;
8. implement SDR details, CDR correlation and anomaly detection;
9. integrate session details and expandable CDR cards;
10. implement duration and timezone formatting;
11. implement statistics queries, charts and drill-down;
12. implement App Admin settings UI with encrypted credential persistence and audit;
13. report source availability through existing health/status facilities;
14. follow existing logging and testing conventions;
15. update the appropriate existing documentation;
16. provide separate source-index recommendations without applying them.

The implementing LLM must preserve the source-database immutability requirement throughout every stage.

---

# 35. Confirmed integration decisions

The following decisions were confirmed for this specification:

- Frontend route: `/admin/cdr`; API namespace: `/api/admin/cdr/`.
- Settings are maintained through an App Admin-only settings page in the existing application; Django Admin is not used.
- The source database connection profile and encrypted credential are stored in the Telephony Toolbox application database. The encryption key is kept outside that database in protected deployment configuration. Plaintext credentials must never be stored or returned.
- Configuration changes are recorded through the existing audit system. Searches and individual record views are not audited.
- Verification follows existing Telephony Toolbox conventions: backend tests and applicable frontend lint/build checks.
