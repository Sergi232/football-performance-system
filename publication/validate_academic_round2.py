"""Second reproducible academic audit with privacy-safe, alias-only output.

This audit inspects the existing materializations. It does not fit models, alter
weights, derive a new score, or turn descriptive differences into recommendations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.presentation import build_player_aliases  # noqa: E402

DB = ROOT / "data" / "football_performance.duckdb"
RATING_VERSION = "match_rating_v0.5-candidate"
ENGINE_VERSION = "expert_0.7.0"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def audit_denominators(con: duckdb.DuckDBPyConnection) -> None:
    """Make the rating and expert-system reporting universes explicit."""
    total = con.execute("SELECT COUNT(*) FROM player_match").fetchone()[0]
    played = con.execute(
        "SELECT COUNT(*) FROM player_match WHERE minutes_played > 0"
    ).fetchone()[0]
    unused_substitutes = con.execute(
        """
        SELECT COUNT(*)
        FROM player_match
        WHERE minutes_played = 0
          AND started = FALSE
          AND primary_role IS NULL
        """
    ).fetchone()[0]
    rating_rows = con.execute(
        "SELECT COUNT(*) FROM player_match_rating WHERE match_rating_version=?",
        [RATING_VERSION],
    ).fetchone()[0]
    expert_records = con.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT DISTINCT match_id, player_id
            FROM decision_results
            WHERE engine_version=?
        )
        """,
        [ENGINE_VERSION],
    ).fetchone()[0]

    require(total == played + unused_substitutes, "Unexpected player_match denominator split")
    require(rating_rows == played, "Match Rating must cover played appearances only")
    require(expert_records == total, "Expert engine must cover the roster/lineup universe")

    print("\n0. DENOMINADORES")
    print(f"player_match (plantilla/alineación): {total}")
    print(f"Apariciones jugadas (minutes_played > 0): {played}")
    print(
        "Suplentes no utilizados "
        "(started=false, minutes_played=0, primary_role=NULL): "
        f"{unused_substitutes}"
    )
    print(f"Match Rating V5: {rating_rows} apariciones jugadas")
    print(f"Motor experto: {expert_records} registros de plantilla/alineación")


def compact(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    if isinstance(value, (float, int)):
        return f"{float(value):.{digits}f}"
    return str(value)


def aliases(db: Path) -> tuple[str, dict[str, str]]:
    with duckdb.connect(str(db), read_only=True) as con:
        team_id = str(con.execute("SELECT team_id FROM player_match ORDER BY team_id LIMIT 1").fetchone()[0])
        squad = con.execute(
            """SELECT p.player_id, p.display_name AS player, COUNT(*) AS appearances
               FROM player_match pm JOIN players p ON p.player_id=pm.player_id
               WHERE pm.team_id=? GROUP BY 1,2 ORDER BY appearances DESC, p.player_id""", [team_id]
        ).df()
    return team_id, build_player_aliases(squad)


def player_label(player_id: object, alias: dict[str, str]) -> str:
    return alias.get(str(player_id), "Jugador")


def position_performance(con: duckdb.DuckDBPyConnection, team_id: str, alias: dict[str, str]) -> None:
    frame = con.execute(
        """
        WITH reliable AS (
            SELECT r.player_id, r.position_group, r.match_date, r.minutes_played, r.match_rating_10,
                   ROW_NUMBER() OVER (PARTITION BY r.player_id, r.position_group ORDER BY r.match_date, r.match_id) AS seq
            FROM player_match_rating r
            WHERE r.team_id=? AND r.match_rating_version=?
              AND r.rating_path IN ('OUTFIELD_PERF18_ANCHORED','GOALKEEPER_PERF18_SHOT90_DIST10')
        ), multi AS (SELECT player_id FROM reliable GROUP BY player_id HAVING COUNT(DISTINCT position_group) > 1)
        SELECT player_id, position_group, COUNT(*) AS appearances, SUM(minutes_played) AS minutes,
               AVG(match_rating_10) AS rating_mean, STDDEV_POP(match_rating_10) AS rating_sd,
               CASE WHEN COUNT(*) >= 3 THEN REGR_SLOPE(match_rating_10, seq) END AS temporal_slope
        FROM reliable WHERE player_id IN (SELECT player_id FROM multi)
        GROUP BY player_id, position_group ORDER BY player_id, appearances DESC, position_group
        """, [team_id, RATING_VERSION]).df()
    require(not frame.empty, "No multi-position reliable player case found")
    frame["Jugador"] = frame["player_id"].map(lambda x: player_label(x, alias))
    show = frame[["Jugador", "position_group", "appearances", "minutes", "rating_mean", "rating_sd", "temporal_slope"]].copy()
    show["Muestra"] = show["appearances"].map(
        lambda n: "MUESTRA PEQUEÑA (1–4)" if n <= 4 else "Muestra descriptiva"
    )
    show.columns = ["Jugador", "Posición observada", "Apariciones", "Minutos", "Rating medio", "DE", "Tendencia/rating-partido", "Muestra"]
    print("\n1. RENDIMIENTO DESCRIPTIVO POR POSICIÓN OBSERVADA")
    print(show.to_string(index=False, formatters={c: lambda x: compact(x) for c in ["Minutos", "Rating medio", "DE", "Tendencia/rating-partido"]}))
    print("Interpretación: diferencias descriptivas por muestra; no se infiere ni recomienda una posición óptima. Las filas de 1–4 apariciones no sostienen tendencias ni interpretaciones fuertes.")


def expert_coverage(con: duckdb.DuckDBPyConnection) -> None:
    pm = con.execute(
        "SELECT COUNT(DISTINCT (match_id, player_id)) FROM decision_results WHERE engine_version=?", [ENGINE_VERSION]
    ).fetchone()[0]
    families = con.execute(
        """
        SELECT regexp_extract(node_id, '^(N[0-9]+)', 1) AS family,
               COUNT(*) AS rows, COUNT(DISTINCT node_id) AS nodes,
               COUNT(DISTINCT (match_id, player_id)) AS player_matches
        FROM decision_results WHERE engine_version=? GROUP BY 1 ORDER BY family
        """, [ENGINE_VERSION]).df()
    evidence = con.execute(
        """SELECT result_value, COUNT(*) AS cases FROM decision_results
            WHERE engine_version=? AND node_id='N13000.100' GROUP BY 1 ORDER BY cases DESC""", [ENGINE_VERSION]).df()
    abstentions = con.execute(
        """SELECT result_value AS reason, COUNT(*) AS cases FROM decision_results
            WHERE engine_version=? AND node_id='N13000.120' GROUP BY 1 ORDER BY cases DESC""", [ENGINE_VERSION]).df()
    require(pm > 0 and not families.empty and not abstentions.empty, "Expert coverage materialization is incomplete")
    print("\n2. COBERTURA DEL SISTEMA EXPERTO")
    print(f"player-match evaluados: {pm}")
    print("Cobertura por familia:")
    print(families.to_string(index=False))
    print("Disponibilidad de evidencia N13000.100:")
    print(evidence.to_string(index=False))
    print("Abstenciones finales N13000.120:")
    print(abstentions.to_string(index=False))


def rating_stability(con: duckdb.DuckDBPyConnection, team_id: str, alias: dict[str, str]) -> None:
    ratings = con.execute(
        """SELECT r.player_id, r.match_id, r.match_date, r.position_group, r.rating_path, r.minutes_played,
                   r.match_rating_10, r.match_rating_confidence, rs.goals, rs.assists, rs.shots_total,
                   rs.turnovers, rs.dispossessed
            FROM player_match_rating r
            LEFT JOIN player_match_raw_stats rs ON rs.match_id=r.match_id AND rs.player_id=r.player_id AND rs.team_id=r.team_id
            WHERE r.team_id=? AND r.match_rating_version=? ORDER BY r.player_id, r.match_date, r.match_id""",
        [team_id, RATING_VERSION]).df()
    require(not ratings.empty, "No Match Rating materialization found")
    ratings["Jugador"] = ratings.player_id.map(lambda x: player_label(x, alias))
    global_stats = ratings.match_rating_10.agg(["count", "mean", "median", "std", "min", "max"])
    by_position = ratings.groupby("position_group").match_rating_10.agg(["count", "mean", "median", "std"]).reset_index()
    intra = ratings.groupby("Jugador").match_rating_10.agg(["count", "std"]).query("count >= 2").sort_values("std", ascending=False).head(5)
    ratings["previous"] = ratings.groupby("player_id").match_rating_10.shift(1)
    for column in ["goals", "assists", "shots_total", "turnovers", "dispossessed"]:
        ratings[f"previous_{column}"] = ratings.groupby("player_id")[column].shift(1)
    ratings["change"] = ratings.match_rating_10 - ratings.previous
    jumps = ratings.dropna(subset=["change"]).assign(abs_change=lambda x: x.change.abs()).nlargest(5, "abs_change")
    q1, q3 = ratings.match_rating_10.quantile([.25, .75])
    low, high = float(q1 - 1.5 * (q3-q1)), float(q3 + 1.5 * (q3-q1))
    outliers = ratings.loc[(ratings.match_rating_10 < low) | (ratings.match_rating_10 > high)]
    print("\n3. ESTABILIDAD TEMPORAL DEL MATCH RATING")
    print("global=" + ", ".join(f"{k}:{compact(v)}" for k, v in global_stats.items()))
    print("por posición observada:")
    print(by_position.to_string(index=False, formatters={c: lambda x: compact(x) for c in ["mean", "median", "std"]}))
    print("mayor variabilidad intra-jugador:")
    print(intra.reset_index().to_string(index=False, formatters={"std": lambda x: compact(x)}))
    print("mayores cambios entre partidos consecutivos:")
    print(jumps[["Jugador", "position_group", "minutes_played", "rating_path", "previous", "match_rating_10", "change", "goals", "previous_goals", "assists", "previous_assists", "turnovers", "previous_turnovers"]].to_string(index=False, formatters={c: lambda x: compact(x) for c in ["minutes_played", "previous", "match_rating_10", "change", "goals", "previous_goals", "assists", "previous_assists", "turnovers", "previous_turnovers"]}))
    print(f"outliers IQR={len(outliers)}; límites descriptivos [{compact(low)}, {compact(high)}]")
    if not outliers.empty:
        print("causa a revisar: los outliers se conservan como casos de revisión; se informa ruta y minutos antes de cualquier cambio.")


def progressive_layers(con: duckdb.DuckDBPyConnection, team_id: str, alias: dict[str, str]) -> None:
    cases = con.execute(
        """
        WITH candidates AS (
          SELECT r.*, pm.primary_role, rs.passes_total, rs.passes_completed, rs.goals, rs.assists,
                 f.feature_value AS pass_completion, a.comparison_scope, a.evidence_state, a.baseline_mean,
                 ROW_NUMBER() OVER (PARTITION BY r.rating_path ORDER BY r.match_date DESC, r.player_id) AS rn
          FROM player_match_rating r
          JOIN player_match pm ON pm.match_id=r.match_id AND pm.player_id=r.player_id AND pm.team_id=r.team_id
          LEFT JOIN player_match_raw_stats rs ON rs.match_id=r.match_id AND rs.player_id=r.player_id AND rs.team_id=r.team_id
          LEFT JOIN player_match_features f ON f.match_id=r.match_id AND f.player_id=r.player_id AND f.feature_name='pass_completion_rate'
          LEFT JOIN analytics_evidence a ON a.match_id=r.match_id AND a.player_id=r.player_id AND a.feature_name='pass_completion_rate'
          WHERE r.team_id=? AND r.match_rating_version=?
        ) SELECT * FROM candidates WHERE rn=1 ORDER BY rating_path
        """, [team_id, RATING_VERSION]).df()
    require(len(cases) >= 3, "Three representative rating routes are not available")
    print("\n4. ESTADISTICA SIMPLE -> SISTEMA COMPLETO")
    for row in cases.itertuples(index=False):
        expert = con.execute(
            """SELECT result_value FROM decision_results WHERE engine_version=? AND match_id=? AND player_id=?
                AND node_id='N13000.120'""", [ENGINE_VERSION, row.match_id, row.player_id]).fetchone()
        coach = "perfil y evidencia descriptiva consultables; no recomendación táctica"
        print(
            f"{player_label(row.player_id, alias)} | ruta={row.rating_path}\n"
            f"  bruto/per90: pases {compact(row.passes_completed,0)}/{compact(row.passes_total,0)}, goles {compact(row.goals,0)}, asistencias {compact(row.assists,0)}\n"
            f"  feature histórica: precisión de pase={compact(row.pass_completion)}\n"
            f"  analytics: {row.comparison_scope or '—'}; baseline={compact(row.baseline_mean)}; estado={row.evidence_state or '—'}\n"
            f"  Match Rating: {compact(row.match_rating_10)}/10; confianza={compact(row.match_rating_confidence,0)}%; rol observado={row.primary_role or '—'}\n"
            f"  sistema experto: {expert[0] if expert else 'sin estado final'}\n"
            f"  Coach: {coach}"
        )


def edge_cases(con: duckdb.DuckDBPyConnection, team_id: str, alias: dict[str, str]) -> None:
    checks = [
        ("Portero", "ruta GK específica", "rating_path='GOALKEEPER_PERF18_SHOT90_DIST10'"),
        ("Pocos minutos", "rating disponible con confianza menor; sin conclusión forzada", "minutes_played <= 15"),
        ("Sin rol fiable", "fallback explícito, sin posición inventada", "rating_path='OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2'"),
        ("Sin GPS", "N9000=GPS_NOT_AVAILABLE y resto del flujo continúa", "n9000='GPS_NOT_AVAILABLE'"),
        ("Varias posiciones", "resumen descriptivo por posición observada", "multi_position"),
        ("Poco historial", "N13000 se abstiene", "low_history"),
    ]
    ratings = con.execute("SELECT * FROM player_match_rating WHERE team_id=? AND match_rating_version=?", [team_id, RATING_VERSION]).df()
    n9000 = con.execute("SELECT match_id, player_id FROM decision_results WHERE engine_version=? AND node_id='N9000.100' AND result_value='GPS_NOT_AVAILABLE' LIMIT 1", [ENGINE_VERSION]).fetchone()
    multi = con.execute("SELECT player_id FROM player_match_rating WHERE team_id=? AND match_rating_version=? AND position_group <> 'OTHER_OUTFIELD' GROUP BY player_id HAVING COUNT(DISTINCT position_group)>1 LIMIT 1", [team_id, RATING_VERSION]).fetchone()
    low = con.execute("SELECT player_id FROM decision_results WHERE engine_version=? AND node_id='N13000.120' AND result_value LIKE 'RECOMMENDATION_NOT_ISSUED%' LIMIT 1", [ENGINE_VERSION]).fetchone()
    actual = [
        ratings.loc[ratings.rating_path.eq('GOALKEEPER_PERF18_SHOT90_DIST10'), 'player_id'].iloc[0] if (ratings.rating_path == 'GOALKEEPER_PERF18_SHOT90_DIST10').any() else None,
        ratings.loc[ratings.minutes_played.le(15), 'player_id'].iloc[0] if (ratings.minutes_played <= 15).any() else None,
        ratings.loc[ratings.rating_path.eq('OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2'), 'player_id'].iloc[0] if (ratings.rating_path == 'OUTFIELD_ROLE_UNAVAILABLE_FALLBACK_V2').any() else None,
        n9000[1] if n9000 else None,
        multi[0] if multi else None,
        low[0] if low else None,
    ]
    print("\n5. CASOS LÍMITE")
    print("Caso | Entrada | Comportamiento esperado | Comportamiento real | Estado")
    for (title, expected, _), player_id in zip(checks, actual):
        ok = player_id is not None
        print(f"{title} | {player_label(player_id, alias) if ok else 'sin caso'} | {expected} | {'evidencia materializada encontrada' if ok else 'no encontrada'} | {'PASS' if ok else 'FAIL'}")
    require(all(x is not None for x in actual), "At least one edge-case contract is missing")


def main() -> None:
    parser = argparse.ArgumentParser(description="Alias-only second academic audit")
    parser.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args()
    db = args.db.expanduser().resolve()
    require(db.exists(), f"Missing DB: {db}")
    team_id, alias = aliases(db)
    print("SECOND ACADEMIC VALIDATION — ALIAS-ONLY OUTPUT")
    print("team=Equipo Demo; identity_policy=Jugador NN / Rival NN")
    with duckdb.connect(str(db), read_only=True) as con:
        audit_denominators(con)
        position_performance(con, team_id, alias)
        expert_coverage(con)
        rating_stability(con, team_id, alias)
        progressive_layers(con, team_id, alias)
        edge_cases(con, team_id, alias)
    print("SECOND ACADEMIC VALIDATION: PASS")


if __name__ == "__main__":
    main()
