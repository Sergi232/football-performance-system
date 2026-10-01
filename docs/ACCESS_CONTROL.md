# Access Control / Multi-tenant Architecture

## Objective

Football Performance System must support multiple clubs and multiple teams without exposing one customer's data to another customer.

The product model is:

```text
authenticated user
→ organisation / club
→ authorised team set
→ authorised product modules
→ dashboard / player / match / GPS / assistant / PDF
```

The current MVP implements the **team authorisation boundary**. Production authentication (passwords, sessions, password recovery, email verification, etc.) is intentionally separate and is not yet implemented.

## Roles

### SUPERADMIN

Internal FPS administrator. May access every organisation and team.

### CLUB_ADMIN

Club-level administrator. May access the teams assigned to the club/account according to the commercial entitlement.

Examples:

```text
Club A
├── First team
├── Reserve team
├── U19 A
└── U19 B
```

A CLUB_ADMIN may receive all four teams, or only the teams covered by the agreement.

### STAFF

Technical staff member. May access only explicitly assigned teams.

Examples:

```text
Head coach first team → First team only
Academy coordinator   → U19 A + U19 B
Analyst reserve team  → Reserve team only
```

## Security rule

Authorisation is server-side. A page must not load every team and merely hide unauthorised ones in the selector.

The current contract is:

```text
access context
→ filter authorised team IDs
→ expose only authorised teams to UI
→ reject direct queries for non-authorised team IDs
```

Restricted roles fail closed: if no teams are assigned, zero teams are visible.

## Current MVP scaffold

`app/access_control.py` provides:

- `AccessContext`;
- roles `SUPERADMIN`, `CLUB_ADMIN`, `STAFF`;
- authorised-team filtering;
- direct team-access assertion;
- fail-closed behaviour for restricted users.

Local environment variables simulate a future authenticated session:

```text
FPS_ACCESS_USER_ID
FPS_ACCESS_ROLE
FPS_ORGANIZATION_ID
FPS_ALLOWED_TEAM_IDS
```

Example restricted staff session:

```powershell
$env:FPS_ACCESS_USER_ID="coach-001"
$env:FPS_ACCESS_ROLE="STAFF"
$env:FPS_ALLOWED_TEAM_IDS="team-id-1"
```

Example club administrator with several contracted teams:

```powershell
$env:FPS_ACCESS_USER_ID="club-admin-001"
$env:FPS_ACCESS_ROLE="CLUB_ADMIN"
$env:FPS_ORGANIZATION_ID="club-001"
$env:FPS_ALLOWED_TEAM_IDS="team-id-1,team-id-2,team-id-3"
```

These environment variables are a development scaffold, **not production authentication**.

## Target production schema

The final identity/access layer should use records equivalent to:

```text
organizations
-------------
organization_id
name
active

teams
-----
team_id
organization_id
name
active

users
-----
user_id
email
password_hash OR external_auth_id
active

user_organizations
------------------
user_id
organization_id
role

user_teams
----------
user_id
team_id
role

entitlements
------------
organization_id
team_id (nullable for organisation-wide entitlement)
module
active
```

Passwords must never be stored in plaintext. Prefer a mature authentication provider or framework rather than implementing password cryptography manually.

## Future module entitlements

Team access and feature access are separate concepts. A future contract may allow:

```text
First team
├── Dashboard       yes
├── Match Rating    yes
├── Assistant IA    yes
├── GPS             yes
└── PDF             yes

U19 A
├── Dashboard       yes
├── Match Rating    yes
├── Assistant IA    no
├── GPS             no
└── PDF             yes
```

Module entitlements are not required for the current TFM MVP and must not be confused with the team authorisation boundary.

## Authentication still pending

Not yet implemented:

- login form;
- password hashing/storage;
- session persistence;
- password reset;
- invitation emails;
- account administration UI;
- billing/subscription integration;
- production audit log.

These can be added later without changing the analytical architecture because pages now consume an authorised team scope rather than assuming global access.

## Validation

Run:

```powershell
python .\app\validate_access_control.py
```

The contract verifies:

- SUPERADMIN can see all teams;
- STAFF can be limited to one team;
- direct access to another team is rejected;
- a restricted user without assignments sees zero teams;
- CLUB_ADMIN can receive a multi-team scope.
