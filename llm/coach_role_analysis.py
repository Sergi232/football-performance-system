"""Deterministic role-aware comparisons for Coach Copilot.

This module answers descriptive questions such as:
- "compara las principales estadísticas de los delanteros"
- "quién ha rendido mejor como central, muéstrame las métricas"

No new football score is created. When the user asks who performed better, the
explicit criterion is the already-approved Match Rating averaged across the selected
role sample. Other fields are shown only as descriptive supporting metrics.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from app.access_control import assert_team_access
from app.data_access import connect_read_only
from app.match_rating_access import MATCH_RATING_VERSION


ROLE_LABELS = {
    "GK": "porteros",
    "CB": "centrales",
    "FB": "laterales/carrileros",
    "DM": "mediocentros defensivos",
    "CM": "centrocampistas",
    "AM": "mediapuntas",
    "W": "extremos",
    "ST": "delanteros",
}

# Exact position_group values accepted by the Match Rating layer. The synthetic
# public demo uses combined groups for a few roles, while the professional case may
# use the more granular groups.
ROLE_GROUP_VALUES = {
    "GK": ("GK",),
    "CB": ("CB",),
    "FB": ("FB", "WB", "FB_WB"),
    "DM": ("DM", "DM_CM"),
    "CM": ("CM", "DM_CM"),
    "AM": ("AM", "AM_W"),
    "W": ("W", "AM_W"),
    "ST": ("ST",),
}

ROLE_ALIASES = (
    ("mediocentros defensivos", "DM"),
    ("mediocentro defensivo", "DM"),
    ("defensas centrales", "CB"),
    ("defensa central", "CB"),
    ("delanteros centro", "ST"),
    ("delantero centro", "ST"),
    ("centrocampistas", "CM"),
    ("centrocampista", "CM"),
    ("mediocentros", "CM"),
    ("mediocentro", "CM"),
    ("guardametas", "GK"),
    ("guardameta", "GK"),
    ("carrileros", "FB"),
    ("carrilero", "FB"),
    ("laterales", "FB"),
    ("lateral", "FB"),
    ("mediapuntas", "AM"),
    ("mediapunta", "AM"),
    ("interiores", "CM"),
    ("interior", "CM"),
    ("extremos", "W"),
    ("extremo", "W"),
    ("centrales", "CB"),
    ("central", "CB"),
    ("delanteros", "ST"),
    ("delantero", "ST"),
    ("atacantes", "ST"),
    ("atacante", "ST"),
    ("pivotes", "DM"),
    ("pivote", "DM"),
    ("porteros", "GK"),
    ("portero", "GK"),
    ("punta", "ST"),
)


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", text).strip()


def role_from_text(text: object) -> str | None:
    q = _norm(text)
    for alias, role in ROLE_ALIASES:
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", q):
            return role
    return None


def _window(text: object) -> int | None:
    q = _norm(text)
    for pattern in (r"ultim\w*\s+(\d{1,2})\s+partid", r"(\d{1,2})\s+ultim\w*\s+partid"):
        match = re.search(pattern, q)
        if match:
            return max(1, min(int(match.group(1)), 50))
    return None


def _anchor_from_history(history: list[dict[str, Any]] | None) -> str | None:
    for item in reversed(history or []):
        if str(item.get("role") or "") != "user":
            continue
        text = str(item.get("content") or "").strip()
        if text and role_from_text(text):
            return text
    return None


def _is_compare_followup(text: object) -> bool:
    q = _norm(text)
    return q in {
        "si comparalos", "si, comparalos", "comparalos", "compara los", "comparalos entonces",
        "muestrame las metricas", "muestra las metricas", "y comparalos", "y las metricas",
    }


def _is_evidence_followup(text: object) -> bool:
    q = _norm(text)
    return any(token in q for token in ("evidencia", "evidencias", "en que te basas", "de donde sale", "que datos usaste"))


def _is_role_query(text: object) -> bool:
    q = _norm(text)
    if role_from_text(q) is None:
        return False
    signals = (
        "compara", "comparar", "comparacion", "estadistic", "metric", "rendimiento", "rendido",
        "mejor", "peor", "quien", "ranking", "lista", "jugadores", "principales", "datos",
    )
    return any(token in q for token in signals)


def _fmt_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except Exception:
        return str(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.{decimals}f}".rstrip("0").rstrip(".")


def _fetch_role_rows(db_path: Path, team_id: str, role: str, last_n_matches: int | None = None) -> list[dict[str, Any]]:
    assert_team_access(team_id)
    groups = ROLE_GROUP_VALUES[role]
    placeholders = ",".join("?" for _ in groups)
    recent_limit = int(last_n_matches or 100000)
    params: list[Any] = [team_id, recent_limit, MATCH_RATING_VERSION, team_id, *groups]

    with connect_read_only(db_path) as con:
        frame = con.execute(
            f"""
            WITH recent AS (
                SELECT tm.match_id
                FROM team_match tm
                JOIN matches m ON m.match_id=tm.match_id
                WHERE tm.team_id=?
                ORDER BY m.match_date DESC, m.match_id DESC
                LIMIT ?
            ), base AS (
                SELECT
                    p.player_id,
                    p.display_name AS player,
                    r.position_group,
                    pm.match_id,
                    m.match_date,
                    pm.minutes_played AS minutes,
                    r.match_rating_10,
                    rs.goals,
                    rs.assists,
                    rs.shots_total,
                    rs.passes_total,
                    rs.passes_completed,
                    rs.tackles_total,
                    rs.tackles_won,
                    rs.interceptions,
                    rs.turnovers,
                    rs.dispossessed,
                    rs.saves,
                    rs.goals_conceded
                FROM player_match_rating r
                JOIN player_match pm
                  ON pm.match_id=r.match_id AND pm.player_id=r.player_id AND pm.team_id=r.team_id
                JOIN players p ON p.player_id=r.player_id
                JOIN matches m ON m.match_id=r.match_id
                LEFT JOIN player_match_raw_stats rs
                  ON rs.match_id=pm.match_id AND rs.player_id=pm.player_id AND rs.team_id=pm.team_id
                WHERE r.match_rating_version=?
                  AND r.team_id=?
                  AND pm.minutes_played > 0
                  AND UPPER(COALESCE(r.position_group,'')) IN ({placeholders})
                  AND r.match_id IN (SELECT match_id FROM recent)
            )
            SELECT
                player_id,
                player,
                string_agg(DISTINCT position_group, ', ' ORDER BY position_group) AS role_groups,
                COUNT(DISTINCT match_id) AS appearances,
                SUM(minutes) AS minutes,
                AVG(match_rating_10) AS avg_rating,
                arg_max(match_rating_10, match_date) AS latest_rating,
                SUM(COALESCE(goals,0)) AS goals,
                SUM(COALESCE(assists,0)) AS assists,
                SUM(COALESCE(shots_total,0)) AS shots,
                SUM(COALESCE(passes_total,0)) AS passes_total,
                SUM(COALESCE(passes_completed,0)) AS passes_completed,
                CASE WHEN SUM(COALESCE(passes_total,0)) > 0
                     THEN 100.0 * SUM(COALESCE(passes_completed,0)) / SUM(COALESCE(passes_total,0))
                     ELSE NULL END AS pass_accuracy,
                SUM(COALESCE(tackles_total,0)) AS tackles_total,
                SUM(COALESCE(tackles_won,0)) AS tackles_won,
                SUM(COALESCE(interceptions,0)) AS interceptions,
                SUM(COALESCE(turnovers,0)) AS turnovers,
                SUM(COALESCE(dispossessed,0)) AS dispossessed,
                SUM(COALESCE(saves,0)) AS saves,
                SUM(COALESCE(goals_conceded,0)) AS goals_conceded
            FROM base
            GROUP BY player_id, player
            ORDER BY avg_rating DESC NULLS LAST, minutes DESC, player
            """,
            params,
        ).df()
    return frame.to_dict("records")


def _metric_parts(role: str, row: dict[str, Any]) -> list[str]:
    common = [
        f"rating medio {_fmt_number(row.get('avg_rating'))}/10",
        f"{_fmt_number(row.get('minutes'), 0)} min",
    ]
    if role == "ST":
        return common + [
            f"{_fmt_number(row.get('goals'), 0)} goles",
            f"{_fmt_number(row.get('assists'), 0)} asist.",
            f"{_fmt_number(row.get('shots'), 0)} remates",
        ]
    if role == "CB":
        return common + [
            f"{_fmt_number(row.get('tackles_won'), 0)} entradas ganadas",
            f"{_fmt_number(row.get('interceptions'), 0)} intercepciones",
            f"{_fmt_number(row.get('pass_accuracy'))}% pase",
            f"{_fmt_number(row.get('turnovers'), 0)} pérdidas",
        ]
    if role == "FB":
        return common + [
            f"{_fmt_number(row.get('assists'), 0)} asist.",
            f"{_fmt_number(row.get('tackles_won'), 0)} entradas ganadas",
            f"{_fmt_number(row.get('interceptions'), 0)} intercepciones",
            f"{_fmt_number(row.get('pass_accuracy'))}% pase",
        ]
    if role in {"DM", "CM"}:
        return common + [
            f"{_fmt_number(row.get('passes_completed'), 0)} pases completados",
            f"{_fmt_number(row.get('pass_accuracy'))}% pase",
            f"{_fmt_number(row.get('tackles_won'), 0)} entradas ganadas",
            f"{_fmt_number(row.get('interceptions'), 0)} intercepciones",
            f"{_fmt_number(row.get('assists'), 0)} asist.",
        ]
    if role in {"AM", "W"}:
        return common + [
            f"{_fmt_number(row.get('goals'), 0)} goles",
            f"{_fmt_number(row.get('assists'), 0)} asist.",
            f"{_fmt_number(row.get('shots'), 0)} remates",
            f"{_fmt_number(row.get('passes_completed'), 0)} pases completados",
        ]
    return common + [
        f"{_fmt_number(row.get('saves'), 0)} paradas",
        f"{_fmt_number(row.get('goals_conceded'), 0)} goles encajados",
        f"{_fmt_number(row.get('pass_accuracy'))}% pase",
    ]


def _wants_best(text: object) -> bool:
    q = _norm(text)
    return any(token in q for token in ("mejor", "rendido mejor", "rendimiento", "quien ha rendido", "quien rinde"))


def try_role_query(
    question: str,
    *,
    db_path: Path,
    team_id: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Return a deterministic role-comparison answer, or None if not applicable."""
    current = str(question or "").strip()
    anchor = current
    role = role_from_text(current)

    if role is None and (_is_compare_followup(current) or _is_evidence_followup(current)):
        prior = _anchor_from_history(history)
        if prior:
            anchor = prior
            role = role_from_text(prior)

    if role is None:
        return None
    if not _is_role_query(anchor) and not _is_compare_followup(current) and not _is_evidence_followup(current):
        return None

    window = _window(current) or _window(anchor)
    rows = _fetch_role_rows(Path(db_path).expanduser().resolve(), str(team_id), role, window)
    role_label = ROLE_LABELS[role]
    scope = f" en los últimos {window} partidos del equipo" if window else " en el periodo disponible"

    if _is_evidence_followup(current):
        return {
            "text": (
                f"La comparación de {role_label} usa el grupo posicional materializado del Match Rating, "
                f"player_match y player_match_raw_stats{scope}. Si se ordena por rendimiento, el criterio explícito "
                "es Match Rating medio; las demás métricas son descriptivas y no forman un score nuevo."
            ),
            "tool": "compare_role_players",
            "role": role,
            "rows": rows,
        }

    if not rows:
        return {
            "text": f"No hay suficientes apariciones con rol {role_label} para construir una comparación válida{scope}.",
            "tool": "compare_role_players",
            "role": role,
            "rows": [],
        }

    visible = rows[:6]
    details = [f"{idx}. {row['player']}: " + ", ".join(_metric_parts(role, row)) for idx, row in enumerate(visible, 1)]

    if _wants_best(anchor):
        leader = visible[0]
        intro = (
            f"Tomando como criterio explícito el Match Rating medio entre los {role_label}, "
            f"{leader['player']} es quien mejor ha rendido{scope} ({_fmt_number(leader.get('avg_rating'))}/10). "
            "Comparación: "
        )
    else:
        intro = f"Comparación descriptiva de {role_label}{scope}: "

    return {
        "text": intro + "; ".join(details) + ".",
        "tool": "compare_role_players",
        "role": role,
        "rows": rows,
    }
