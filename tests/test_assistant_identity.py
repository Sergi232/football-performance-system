import pandas as pd

from app.assistant_identity import build_assistant_identity_context


def _frames():
    squad = pd.DataFrame(
        [
            {"player_id": "P2", "player": "Bruno Bravo"},
            {"player_id": "P1", "player": "Álvaro Alpha"},
        ]
    )
    matches = pd.DataFrame([{"opponent": "Real Example"}, {"opponent": "Club Test"}])
    return squad, matches


def test_alias_to_runtime_uses_canonical_full_player_name(monkeypatch):
    monkeypatch.setenv("FPS_DEMO_MODE", "1")
    squad, matches = _frames()
    ctx = build_assistant_identity_context(
        squad,
        matches,
        raw_team_name="Deportivo Real",
        team_alias="Equipo Demo",
    )

    # Aliases are assigned by stable player_id order: P1 -> Jugador 01.
    runtime = ctx.to_runtime("¿Cómo ha evolucionado Jugador 01?")
    assert "Álvaro Alpha" in runtime
    assert "Jugador 01" not in runtime


def test_display_masks_player_opponent_and_team_case_insensitively(monkeypatch):
    monkeypatch.setenv("FPS_DEMO_MODE", "1")
    squad, matches = _frames()
    ctx = build_assistant_identity_context(
        squad,
        matches,
        raw_team_name="Deportivo Real",
        team_alias="Equipo Demo",
    )

    display = ctx.to_display(
        "álvaro alpha fue el mejor ante REAL EXAMPLE para DEPORTIVO REAL."
    )
    assert "Jugador 01" in display
    assert "Rival" in display
    assert "Equipo Demo" in display
    assert not ctx.leaked_runtime_identities(display)


def test_private_mode_keeps_real_names(monkeypatch):
    monkeypatch.setenv("FPS_DEMO_MODE", "0")
    squad, matches = _frames()
    ctx = build_assistant_identity_context(
        squad,
        matches,
        raw_team_name="Deportivo Real",
        team_alias="Equipo Demo",
    )
    text = "Álvaro Alpha ante Real Example"
    assert ctx.to_display(text) == text
    assert ctx.to_runtime(text) == text
