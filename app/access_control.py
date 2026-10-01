"""Team-scoped authorization primitives for the Streamlit product.

This module is intentionally separate from authentication. It answers only:
"which teams may the current user access?". Production login/password handling
can later populate the same AccessContext from a real identity provider/database.

Local/default behaviour remains SUPERADMIN so development and existing validators
are not broken. Restricted roles fail closed when no team assignment is supplied.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


VALID_ROLES = {"SUPERADMIN", "CLUB_ADMIN", "STAFF"}


class AccessDenied(PermissionError):
    """Raised when a user attempts to access a team outside their entitlement."""


@dataclass(frozen=True)
class AccessContext:
    user_id: str
    role: str
    organization_id: str | None = None
    allowed_team_ids: frozenset[str] | None = None
    source: str = "environment"

    @property
    def unrestricted(self) -> bool:
        return self.role == "SUPERADMIN"


def _parse_team_ids(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def current_access_context() -> AccessContext:
    """Build the current local access context from environment variables.

    Environment contract used for the MVP scaffold:
    - FPS_ACCESS_USER_ID: logical user identifier.
    - FPS_ACCESS_ROLE: SUPERADMIN | CLUB_ADMIN | STAFF.
    - FPS_ORGANIZATION_ID: optional club/organisation identifier.
    - FPS_ALLOWED_TEAM_IDS: comma-separated team IDs for restricted roles.

    SUPERADMIN ignores FPS_ALLOWED_TEAM_IDS. CLUB_ADMIN and STAFF fail closed if
    no team IDs are assigned.
    """
    role = str(os.environ.get("FPS_ACCESS_ROLE", "SUPERADMIN")).strip().upper()
    if role not in VALID_ROLES:
        raise ValueError(f"Unsupported FPS_ACCESS_ROLE: {role}")

    allowed = None if role == "SUPERADMIN" else _parse_team_ids(os.environ.get("FPS_ALLOWED_TEAM_IDS"))
    return AccessContext(
        user_id=str(os.environ.get("FPS_ACCESS_USER_ID", "local-superadmin")).strip() or "local-superadmin",
        role=role,
        organization_id=(str(os.environ.get("FPS_ORGANIZATION_ID", "")).strip() or None),
        allowed_team_ids=allowed,
    )


def team_is_allowed(team_id: object, context: AccessContext | None = None) -> bool:
    ctx = context or current_access_context()
    if ctx.unrestricted:
        return True
    allowed = ctx.allowed_team_ids or frozenset()
    return str(team_id) in allowed


def assert_team_access(team_id: object, context: AccessContext | None = None) -> None:
    ctx = context or current_access_context()
    if team_is_allowed(team_id, ctx):
        return
    raise AccessDenied(
        f"User {ctx.user_id!r} with role {ctx.role} has no access to team {str(team_id)!r}"
    )


def filter_authorized_teams(
    frame: pd.DataFrame,
    context: AccessContext | None = None,
    *,
    team_id_col: str = "team_id",
) -> pd.DataFrame:
    """Return only teams authorized for the supplied access context."""
    if frame is None:
        return frame
    out = frame.copy()
    if out.empty:
        return out
    if team_id_col not in out.columns:
        raise KeyError(f"Missing team id column: {team_id_col}")

    ctx = context or current_access_context()
    if ctx.unrestricted:
        return out

    allowed = ctx.allowed_team_ids or frozenset()
    if not allowed:
        return out.iloc[0:0].copy()
    mask = out[team_id_col].astype(str).isin(allowed)
    return out.loc[mask].copy()


def allowed_team_ids(context: AccessContext | None = None) -> frozenset[str] | None:
    ctx = context or current_access_context()
    return None if ctx.unrestricted else (ctx.allowed_team_ids or frozenset())


def context_for_testing(
    role: str,
    team_ids: Iterable[object] = (),
    *,
    user_id: str = "test-user",
    organization_id: str | None = None,
) -> AccessContext:
    normalized_role = str(role).strip().upper()
    if normalized_role not in VALID_ROLES:
        raise ValueError(f"Unsupported role: {normalized_role}")
    allowed = None if normalized_role == "SUPERADMIN" else frozenset(str(x) for x in team_ids)
    return AccessContext(
        user_id=user_id,
        role=normalized_role,
        organization_id=organization_id,
        allowed_team_ids=allowed,
        source="test",
    )
