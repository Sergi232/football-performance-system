"""Elite technical PDF renderer v6 with descriptive GPS context.

GPS remains optional and downstream of the canonical physical summary layer.
This renderer never turns GPS into fatigue/readiness/injury-risk claims and never
feeds physical values back into Match Rating, Performance Index or expert decisions.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from reports import pdf_engine_elite_v2 as ui
from reports import pdf_engine_elite_v3 as narrative
from reports import pdf_engine_elite_v5 as base_v5


def _num(value: Any) -> float | None:
    return ui._num(value)


def _km(value: Any) -> str:
    number = _num(value)
    return "-" if number is None else f"{number / 1000.0:.2f} km"


def _kmh(value: Any) -> str:
    number = _num(value)
    return "-" if number is None else f"{number * 3.6:.1f} km/h"


def _accel(value: Any) -> str:
    number = _num(value)
    return "-" if number is None else f"{number:.2f} m/s²"


def _minutes(value: Any) -> str:
    number = _num(value)
    return "-" if number is None else f"{number:.0f}'"


def _role(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "Rol no disponible"


def _providers(gps: dict[str, Any]) -> str:
    providers = [str(v) for v in list(gps.get("providers") or []) if str(v).strip()]
    return ", ".join(providers) if providers else "Proveedor no disponible"


def _gps_banner(gps: dict[str, Any], styles) -> Paragraph:
    if gps.get("contains_synthetic_demo"):
        text = (
            "<b>DATOS DEMO · GPS sintético.</b> Valores generados para demostrar el flujo técnico; "
            "no son observaciones reales del deportista ni validan fatiga, readiness o riesgo de lesión."
        )
    else:
        text = (
            "<b>GPS descriptivo.</b> La lectura se limita a distancia, velocidad y aceleración observadas; "
            "no se aplican umbrales automáticos de fatiga, readiness, sprint o riesgo de lesión."
        )
    return Paragraph(text, styles["note"])


def _no_gps(styles) -> list[Any]:
    return [
        Paragraph(
            "No hay datos GPS disponibles para este alcance. El GPS es opcional y su ausencia no bloquea el informe técnico.",
            styles["note"],
        )
    ]


def _team_gps_page(payload: dict[str, Any], styles, width: float) -> list[Any]:
    gps = dict(payload.get("gps") or {})
    story: list[Any] = [PageBreak()]
    story += ui._section(
        "07 · Físico / GPS",
        "Carga externa descriptiva del último partido con GPS y cobertura reciente. No modifica la evaluación técnica.",
        width,
        styles,
    )
    if not gps.get("available"):
        return story + _no_gps(styles)

    story.append(_gps_banner(gps, styles))
    story.append(Spacer(1, 3 * mm))

    players = list(gps.get("latest_match_players") or [])
    coverage = list(gps.get("coverage") or [])
    latest_cov = coverage[0] if coverage else {}
    unresolved = sum(1 for row in players if not str(row.get("effective_role") or "").strip())

    story.append(ui._kpi_row([
        ("Cobertura último registro", f"{ui._count(latest_cov.get('gps_players'))}/{ui._count(latest_cov.get('played_players'))}", "Jugadores con GPS / utilizados"),
        ("Proveedor", _providers(gps), "Procedencia del registro"),
        ("Jugadores mostrados", str(len(players)), "Sin ranking físico"),
        ("Rol no disponible", str(unresolved), "Se mantiene sin inferencia artificial"),
    ], width, styles))

    rows = [["Jugador", "Rol", "Min", "Distancia", "V. máx", "Acel. máx", "Decel. máx"]]
    for row in players[:22]:
        rows.append([
            ui._safe(row.get("player")),
            _role(row.get("effective_role")),
            _minutes(row.get("minutes_played")),
            _km(row.get("total_distance_m")),
            _kmh(row.get("peak_speed_m_s")),
            _accel(row.get("max_acceleration_m_s2")),
            _accel(row.get("min_acceleration_m_s2")),
        ])
    story.append(Spacer(1, 3 * mm))
    story.append(ui._compact_table(rows, [30*mm, 37*mm, 14*mm, 25*mm, 24*mm, 24*mm, 24*mm], styles))

    story.append(Spacer(1, 3 * mm))
    story.append(narrative._review_box(
        "Claves para la revisión física",
        [
            f"Cobertura: {ui._count(latest_cov.get('gps_players'))} de {ui._count(latest_cov.get('played_players'))} jugadores utilizados tienen registro GPS en el último alcance mostrado.",
            f"Contexto: cada fila conserva minutos y rol cuando la fuente lo permite; {unresolved} registros mantienen el rol como no disponible en lugar de inventarlo.",
            "Uso recomendado: revisar cambios físicos junto al contexto de minutos, rol y vídeo; estas métricas no diagnostican fatiga ni rendimiento táctico por sí solas.",
        ],
        width,
        styles,
    ))
    return story


def _player_gps_page(payload: dict[str, Any], styles, width: float) -> list[Any]:
    gps = dict(payload.get("gps") or {})
    summary = dict(payload.get("summary") or {})
    name = ui._safe(summary.get("player"), "Jugador")
    story: list[Any] = [PageBreak()]
    story += ui._section(
        "GPS · Perfil físico",
        f"Evolución descriptiva de {name}. Comparar siempre con minutos y rol del propio jugador.",
        width,
        styles,
    )
    if not gps.get("available"):
        return story + _no_gps(styles)

    story.append(_gps_banner(gps, styles))
    story.append(Spacer(1, 3 * mm))
    latest = dict(gps.get("latest") or {})
    history = list(gps.get("history") or [])

    story.append(ui._kpi_row([
        ("Última distancia", _km(latest.get("total_distance_m")), f"{_minutes(latest.get('minutes_played'))} · {_role(latest.get('effective_role'))}"),
        ("Velocidad máxima", _kmh(latest.get("peak_speed_m_s")), "Máximo observado"),
        ("Aceleración máxima", _accel(latest.get("max_acceleration_m_s2")), "Descriptiva"),
        ("Desaceleración máxima", _accel(latest.get("min_acceleration_m_s2")), "Descriptiva"),
    ], width, styles))

    rows = [["Fecha", "Rival", "Rol", "Min", "Distancia", "V. máx"]]
    for row in history[:10]:
        rows.append([
            ui._date(row.get("match_date")),
            ui._safe(row.get("opponent")),
            _role(row.get("effective_role")),
            _minutes(row.get("minutes_played")),
            _km(row.get("total_distance_m")),
            _kmh(row.get("peak_speed_m_s")),
        ])
    story.append(Spacer(1, 3 * mm))
    story.append(ui._compact_table(rows, [26*mm, 42*mm, 41*mm, 16*mm, 27*mm, 25*mm], styles))

    story.append(Spacer(1, 3 * mm))
    story.append(narrative._review_box(
        "Claves para la revisión física",
        [
            f"Último registro: {_km(latest.get('total_distance_m'))} en {_minutes(latest.get('minutes_played'))}, con velocidad máxima de {_kmh(latest.get('peak_speed_m_s'))}.",
            f"Rol de contexto: {_role(latest.get('effective_role'))}. Si el rol no está disponible, no se fuerza una comparación posicional.",
            "La serie sirve para revisar evolución intra-jugador; no establece por sí sola estado de forma, fatiga, readiness ni riesgo de lesión.",
        ],
        width,
        styles,
    ))
    return story


def _match_gps_page(payload: dict[str, Any], styles, width: float) -> list[Any]:
    gps = dict(payload.get("gps") or {})
    match = dict(payload.get("match") or {})
    opponent = ui._safe(match.get("opponent"), "Rival")
    story: list[Any] = [PageBreak()]
    story += ui._section(
        "GPS · Partido",
        f"Carga externa descriptiva frente a {opponent}. Lectura individual sin ranking de calidad.",
        width,
        styles,
    )
    if not gps.get("available"):
        return story + _no_gps(styles)

    story.append(_gps_banner(gps, styles))
    story.append(Spacer(1, 3 * mm))
    players = list(gps.get("players") or [])
    unresolved = sum(1 for row in players if not str(row.get("effective_role") or "").strip())

    story.append(ui._kpi_row([
        ("Jugadores con GPS", str(len(players)), "Registro del partido"),
        ("Proveedor", _providers(gps), "Procedencia"),
        ("Rol disponible", str(len(players) - unresolved), "Con contexto posicional"),
        ("Rol no disponible", str(unresolved), "Sin inferencia artificial"),
    ], width, styles))

    rows = [["Jugador", "Rol", "Min", "Distancia", "V. máx", "Acel. máx", "Decel. máx"]]
    for row in players[:22]:
        rows.append([
            ui._safe(row.get("player")),
            _role(row.get("effective_role")),
            _minutes(row.get("minutes_played")),
            _km(row.get("total_distance_m")),
            _kmh(row.get("peak_speed_m_s")),
            _accel(row.get("max_acceleration_m_s2")),
            _accel(row.get("min_acceleration_m_s2")),
        ])
    story.append(Spacer(1, 3 * mm))
    story.append(ui._compact_table(rows, [30*mm, 37*mm, 14*mm, 25*mm, 24*mm, 24*mm, 24*mm], styles))

    story.append(Spacer(1, 3 * mm))
    story.append(narrative._review_box(
        "Claves para la revisión física",
        [
            f"Cobertura del partido: {len(players)} jugadores con resumen GPS descriptivo.",
            f"Contexto posicional: {len(players) - unresolved} registros con rol disponible y {unresolved} sin rol recuperable de la fuente.",
            "Cruzar la carga externa con minutos, rol y vídeo. No usar esta página como diagnóstico de fatiga o como ranking entre posiciones.",
        ],
        width,
        styles,
    ))
    return story


def render_pdf_bytes(payload: dict[str, Any]) -> bytes:
    report_type = str(payload.get("report_type") or "").lower()
    if report_type not in {"team", "player", "match"}:
        raise ValueError(f"Unsupported report_type: {report_type}")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title="Football Performance System - Informe técnico",
        author="Football Performance System",
    )
    styles = ui._styles()
    width = A4[0] - 32 * mm

    if report_type == "team":
        story = base_v5._team_story(payload, styles, width) + _team_gps_page(payload, styles, width)
    elif report_type == "player":
        story = base_v5._player_story(payload, styles, width) + _player_gps_page(payload, styles, width)
    else:
        story = base_v5._match_story(payload, styles, width) + _match_gps_page(payload, styles, width)

    doc.build(story, onFirstPage=ui._footer, onLaterPages=ui._footer)
    return buffer.getvalue()
