from pathlib import Path

from app.coach_ui import display_text

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_friendly_header_and_internal_token_mapping() -> None:
    assert display_text("TEAM MODE") == "MODO EQUIPO"
    assert display_text("TEAM MODE · CENTRO DE MANDO") == "MODO EQUIPO · CENTRO DE MANDO"
    assert display_text("MATCH MODE · POSTPARTIDO") == "MODO PARTIDO · POSTPARTIDO"
    assert display_text("PLAYER MODE · EQUIPO DEMO") == "MODO JUGADOR · EQUIPO DEMO"
    assert display_text("ANALYTICS · PERFIL HISTÓRICO") == "ANÁLISIS · PERFIL HISTÓRICO"
    assert display_text("COACH COPILOT · LOCAL") == "ASISTENTE IA · LOCAL"
    assert display_text("ATTENTION CENTRE · DATA QUALITY") == "CENTRO DE ATENCIÓN · CALIDAD DE DATOS"
    assert display_text("match_rating_v0.5-candidate") == "Match Rating V5"
    assert display_text("performance_score_v0.2-experimental") == "Performance Index · experimental"
    assert display_text("gps_physical_summary_v0.1-descriptive") == "Resumen físico · v0.1"
    assert display_text("attention_flags_v0.3-auditable") == "Alertas auditables · v0.3"
    assert display_text("GOALKEEPER_SEPARATE_PRO_REFERENCE_SHOT90_DIST10") == "Modelo específico de portero"


def test_match_page_does_not_expose_stale_v2_or_raw_fallback_table_labels() -> None:
    text = _read("app/pages/4_Partit.py")
    assert "conservan el rating V2" not in text
    assert "player\", \"minutes_played\", \"match_rating_10\", \"match_rating_confidence" not in text
    assert "modelo de respaldo de Match Rating V5" in text


def test_player_page_is_spanish_and_localizes_venue() -> None:
    text = _read("app/pages/2_Jugador.py")
    assert '"Shot-stopping"' not in text
    assert "90% shot-stopping" not in text
    assert '"H": "L"' in text
    assert '"A": "V"' in text
    assert "Modelo específico de portero" in text


def test_gps_page_localizes_home_away_codes() -> None:
    text = _read("app/pages/6_Fisic_GPS.py")
    assert '"H": "L"' in text
    assert '"A": "V"' in text
    assert 'show["venue"] = show["venue"].map(venue_short)' in text


def test_attention_messages_are_spanish_and_ui_is_humanized() -> None:
    builder = _read("analytics/build_attention_flags.py")
    page = _read("app/pages/7_Alertes.py")
    for forbidden in ("La font no informa", "Hi ha mostres GPS", "cap posició", "d’aquesta aparició"):
        assert forbidden not in builder
        assert forbidden not in page
    assert "La fuente no informa de un rol táctico fiable" in builder
    assert '"CONTEXT_LIMITATION": "Limitación de contexto"' in page
    assert '"ROLE_CONTEXT_UNAVAILABLE": "Rol no disponible"' in page
    assert '"player_match_rating": "Match Rating"' in page


def test_performance_index_does_not_show_development_jargon() -> None:
    text = _read("app/pages/1_Performance_Index.py")
    assert "en esta baseline" not in text
    assert '"N fallback"' not in text
    assert "Dim. de respaldo" in text


def test_assistant_humanizes_tool_trace_and_avoids_similarity_prompt() -> None:
    text = _read("app/pages/5_Assistent_IA.py")
    assert 'st.write("Herramientas: "' not in text
    assert "Consultas utilizadas:" in text
    assert "Compara descriptivamente dos jugadores que tengan un rol parecido." not in text
