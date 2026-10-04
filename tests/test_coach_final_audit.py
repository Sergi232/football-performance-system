from pathlib import Path
import pytest
from llm import coach_agent_general as agent
from llm import coach_agent_fast as fast
from llm import coach_agent_external as external

@pytest.mark.parametrize('metric', ['goals', 'passes_completed', 'total_distance_m'])
@pytest.mark.parametrize(('phrase','expected'), [('máximo','max'),('mínimo','min'),('último valor','latest')])
def test_explicit_aggregation(metric, phrase, expected):
    assert agent._rank_aggregation(metric, f'Ranking por {phrase} de {metric}') == expected

@pytest.mark.parametrize('module', [fast, external])
@pytest.mark.parametrize('role', ['centrales', 'delanteros', 'porteros'])
@pytest.mark.parametrize('intent', ['¿Quién está más cansado entre los', '¿Quién debería ser titular entre los', '¿Quién tiene riesgo de lesión entre los'])
def test_safety_precedes_role_routing(monkeypatch, module, role, intent):
    def forbidden(*args, **kwargs):
        raise AssertionError('Role tools must not run for blocked intent')
    monkeypatch.setattr(fast, '_try_role_pre_route', forbidden)
    kwargs = dict(db_path=Path('unused.duckdb'), team_id='DEMO')
    if module is external:
        kwargs['api_key'] = ''
    result = module.run_coach_agent_turn(f'{intent} {role}?', **kwargs)
    assert not result.tools_used and result.tool_rounds == 0
    assert 'No puedo' in result.text

def test_full_temporal_query_is_not_a_followup():
    assert not agent._followup('¿Quién tiene más goles en los últimos 5 partidos?')
    assert agent._followup('¿Y en los últimos 5 partidos?')

def test_followup_history_keeps_window_for_evidence():
    history = [dict(role='user',content='¿Quién tiene más goles?'),dict(role='user',content='¿Y en los últimos 3 partidos?')]
    result = fast._collapse_followup_history('¿Qué evidencias tienes?', history)
    assert 'últimos 3 partidos' in result[-1]['content']

def test_rank_answer_respects_order_window_and_requested_count():
    rows = [dict(player=f'Jugador {i:02}', value=i, sample_matches=3) for i in range(1,9)]
    block = dict(metric_label='minutos',aggregation='sum',order='asc',unit='min',last_n_matches=3,rows=rows)
    text = agent._rank_answer('Top 8 con menos minutos', {'rank_players':block})
    assert 'Jugador 08' in text
    assert 'menor a mayor' in text
    assert '3 partidos' in text
    assert 'lidera' not in text


@pytest.mark.parametrize('metric', ['rating', 'goles', 'distancia'])
def test_named_comparison_precedes_global_ranking(monkeypatch, metric):
    monkeypatch.setattr(agent, '_player_mentions', lambda *args: ['Jugador A', 'Jugador B'])
    calls = agent._deterministic_route(None, f'Compara Jugador A y Jugador B: quien tiene más {metric}')
    assert calls == [('compare_players', {'players':['Jugador A','Jugador B']})]

@pytest.mark.parametrize('role', ['central', 'delantero', 'portero'])
def test_undefined_global_criterion_remains_blocked_with_role(role):
    assert fast._policy_block(f'¿Quién es el {role} más completo con más goles?')
