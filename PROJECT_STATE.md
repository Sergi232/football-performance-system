# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este estado documentado.

## 1. Fase actual

```text
Arquitectura base                         HECHO
DATA-01 fixtures + player_match          CERRADO / VALIDADO
DATA-02 lineups + titularidad/rol        CERRADO / VALIDADO
DATA-03 shots + cards                    CERRADO / VALIDADO
DATA-04 player-match raw stats           CERRADO / VALIDADO
COLLECTOR-01 MVP                         CERRADO FUNCIONALMENTE
GPS-01 contrato multi-proveedor          CERRADO / VALIDADO
FEATURE-01 base determinista             CERRADO / VALIDADO
FEATURE-02 evolución temporal            CERRADO / VALIDADO
FEATURE-03 historial condicionado a rol  CERRADO / VALIDADO
EXPERT-01 N1000-N3000                    CERRADO / VALIDADO
EXPERT-02 N4000-N7000                    CERRADO / VALIDADO
EXPERT-03 N8000-N9000                    CERRADO / VALIDADO
EXPERT-04 N10000 rol/encaje              CERRADO / VALIDADO
EXPERT-05 N11000 consistencia/tendencia  CERRADO / VALIDADO
EXPERT-06 N12000 player-fit evidence     CERRADO / VALIDADO
EXPERT-07 N13000 recommendation gate     CERRADO / VALIDADO
MOTOR EXPERTO BASE N1000-N13000          CERRADO / VALIDADO
DASHBOARD-01 Streamlit MVP               DATA CONTRACT PASS / REVISIÓN VISUAL ABIERTA
LLM-01 contexto + asistente seguro       CERRADO / VALIDADO
LLM-02 proveedor OpenAI opcional         PREPARADO / PENDIENTE VALIDACIÓN LOCAL
PDF                                      DESPUÉS DE LLM-02 / DASHBOARD
```

El Collector puede recibir mejoras UX posteriormente, pero su contrato de datos ya no bloquea el desarrollo.

## 2. Producto

Aplicación web para equipos amateur o semiprofesionales sin departamento de análisis:

```text
VÍDEO / DATA COLLECTOR + GPS OPCIONAL
→ BASE DE DATOS
→ FEATURE ENGINE
→ MOTOR ANALÍTICO
→ SISTEMA EXPERTO / ML
→ DASHBOARD
→ ASISTENTE IA
→ INFORMES PDF
```

TEAM MODE es principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura y el sistema principal no depende de datos del rival.

## 3. Principios aprobados

- GPS opcional y complementario.
- Separación estricta raw → features → motor → conclusiones.
- Ninguna conclusión importante depende exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso requiere datos, literatura, validación o experimento.
- No rellenar datos ausentes mediante supuestos silenciosos.
- PannaData/Opta sirve para desarrollar/validar; no define el producto amateur.
- GitHub es la fuente de verdad técnica.
- Priorizar MVP funcional antes de aumentar complejidad.
- No crear scores de fit/recomendación antes de disponer de política validada.

## 4. Arquitectura materializada

```text
collector/       captura manual/vídeo
data/            esquema, imports y datos normalizados
gps/             normalización multi-proveedor
features/        variables deterministas, temporales y condicionadas a rol
decision_tree/   sistema experto auditable
app/             dashboard web Streamlit
llm/             contexto, guardrails y proveedor generativo opcional
models/          ML opcional posterior
reports/         PDF posterior
tests/           regresión y validación
```

DuckDB. Unidad principal: `player_match = jugador + partido`.

Tablas clave: `teams`, `players`, `matches`, `team_match`, `player_match`, `player_role_stints`, `match_events`, `player_match_raw_stats`, `collector_sessions`, `gps_imports`, `gps_player_map`, `gps_observations`, `player_match_features`, `decision_results`.

Versiones de esquema:

```text
0.1.0 core
0.2.0 player_match_raw_stats
0.3.0 tackles_won + goals_conceded
0.4.0 GPS normalization
```

## 5. Caso demostrador

```text
Deportivo Alavés — LaLiga 2025/26
team id: 4dtdjgnpdq9uw4sdutti0vaar
38 partidos
36 jugadores
835 player_match
```

Antes de publicar se anonimizará como TEAM_001 / PLAYER_001 / OPP_001. No se publicarán datasets completos originales de PannaData/Opta.

## 6. DATA — CERRADO

### DATA-01 / DATA-02
- 38 fixtures.
- 835 `player_match`.
- 418 titulares = 38×11.
- 245 suplentes con 0 minutos.
- 36 jugadores.
- no se infiere formación.
- no se crean role stints ficticios.

### DATA-03
`opta_events.parquet` no es feed atómico completo. No se inventan pases, regates, tackles, intercepciones o faltas.

```text
shot_events fuente 464
autogol excluido 1
SHOT importados 463
cobertura 38/38
CARD 98
CARD sin player_id 2
```

`shots_blocked` queda `AGGREGATE_CANONICAL`.

### DATA-04
835/835 filas, 38/38 partidos, 36 jugadores. Validación PASS.

27 raw stats aprobadas: pases total/completados, asistencias, largos, centros, regates, turnovers, dispossessed, remates, bloqueados, goles, tackles total/ganados, intercepciones, blocked passes, despejes, faltas cometidas/recibidas, tarjetas, penaltis concedidos/ganados, paradas y goles encajados.

`key_passes` no tiene columna verificada. No se aproxima. Los NULL se preservan.

### Fechas
`opta_fixtures.match_date` usa `YYYY-MM-DDZ`. Los 38 `matches.match_date` fueron reparados desde fuente real; no se infirió cronología por ID u orden.

## 7. COLLECTOR-01 — CERRADO FUNCIONALMENTE

Catálogo `collector/event_catalog.json` v0.3.0.

Acciones: PASS NORMAL/LONG/CROSS SUCCESS/FAIL; DRIBBLE; SHOT GOAL/ON_TARGET/OFF_TARGET/BLOCKED; TACKLE; INTERCEPTION; BLOCK; CLEARANCE; FOUL; CARD; LOSS OTHER; PENALTY WON/CONCEDED GOAL/MISSED; CORNER FOR/AGAINST; GK SAVE/GOAL_CONCEDED.

Qualifiers: `key_pass`, `assist`, `second_yellow`, `set_piece_result`, `penalty_taker_player_id`.

Decisiones: LONG/CROSS cuentan como pase; PASS FAIL y DRIBBLE FAIL generan pérdida derivada; LOSS solo otras pérdidas; falta peligrosa se derivará desde x/y; clips ABP conservan tiempo partido/vídeo.

`collector/data_collector_futbol_mvp.html`. Validación local PASS 20/20.

## 8. GPS-01 — CERRADO / VALIDADO

Contrato multi-proveedor normalizado. Unidades canónicas: ms, m, m/s, m/s² y x/y cuando el mapping espacial es seguro. Mapping declarativo, conversiones, acumulada→incremental, `gps_player_map`, metadatos y QC. Sin fuzzy matching silencioso ni umbrales sprint/HIE/carga inventados.

`GPS-01 VALIDATION: PASS`.

## 9. FEATURE ENGINE — CERRADO / VALIDADO

### FEATURE-01 — `0.1.0`
28 features: 7 ratios + 21 por90.

```text
FEATURE-01 VALIDATION: PASS
feature rows 23380/23380
non-null 6324
coverage 38 matches / 36 players
```

### FEATURE-02 — `0.2.0`
Por cada feature: `history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`.

```text
FEATURE-02 VALIDATION: PASS
feature rows 163660/163660
coverage 38 / 36
history_n PASS
prior_std PASS
first-date strict-past PASS
```

Strict-past: solo fechas anteriores; partido actual y misma fecha no entran; futuros no entran; NULL no se vuelve 0; sin ventanas arbitrarias 3/5/10.

### FEATURE-03 — `0.3.0`
Historial separado por jugador + rol observado + feature.

```text
FEATURE-03 VALIDATION: PASS
feature rows 117735/117735
non-null 43060
player_match con rol observado 590/835
roles observados distintos 23
role source identity PASS
missing-role NULL PASS
strict-past first-observation PASS
```

No se infiere rol ni se crea score de fit.

## 10. SISTEMA EXPERTO — MOTOR BASE CERRADO

Arquitectura:

```text
N1000  disponibilidad / actividad
N2000  perfil estructural
N3000  forma / evolución
N4000  amenaza ofensiva
N5000  creación / progresión
N6000  contribución defensiva
N7000  finalización
N8000  contexto del equipo
N9000  componente físico opcional
N10000 rol y encaje táctico
N11000 consistencia / tendencia
N12000 player fit evidence
N13000 recommendation gate
```

Cada nodo: `entrada → condición → resultado → confianza → justificación`.

### EXPERT-01 — `expert_0.1.0`
48.430 decisiones. N1000=835, N2000=835, N3000=46.760. Sin duplicados ni etiquetas prematuras.

### EXPERT-02 — `expert_0.2.0`
68.470 decisiones. N4000-N7000 como evidencia descriptiva own-history. Carry-forward exacto PASS.

### EXPERT-03 — `expert_0.3.0`
72.645 decisiones. N8000 contexto propio equipo y N9000 GPS opcional. GPS observado en demo: 0.

### EXPERT-04 — `expert_0.4.0`
94.355 decisiones. N10000 usa FEATURE-03 same-role strict-past. 590/835 player-match con rol observado. Sin fit score.

### EXPERT-05 — `expert_0.5.0`
141.115 decisiones. N11000 expone `prior_std` y `prior_slope` exactos para 28 features. No clasifica consistency/improving/declining sin umbral validado.

### EXPERT-06 — `expert_0.6.0`
151.970 decisiones. N12000=10.855. 501 player-match con evidencia same-role evaluable. Expone cobertura y conteos exactos, no score.

### EXPERT-07 — `expert_0.7.0` — CERRADO / VALIDADO

```text
EXPERT-07 VALIDATION: PASS
player_match rows: 835
N13000 nodes/player-match: 3
decision rows: 154475/154475
N13000 rows: 2505/2505
N13000 outputs checked: 2505
N1000-N12000 exact carry-forward: PASS
recommendation evidence gate identity contract: PASS
recommendation policy remains explicitly unvalidated: PASS
RECOMMENDATION_NOT_ISSUED_NO_EVIDENCE: 89
RECOMMENDATION_NOT_ISSUED_POLICY_UNVALIDATED: 501
RECOMMENDATION_NOT_ISSUED_ROLE_UNKNOWN: 245
```

El motor experto base N1000-N13000 queda completado y validado. Una política futura de recomendación solo podrá sustituir este gate cuando esté justificada con literatura, datos o experimentación.

## 11. DASHBOARD-01 — DATA CONTRACT PASS / REVISIÓN VISUAL ABIERTA

Archivos principales:

```text
app/__init__.py
app/data_access.py
app/validate_dashboard.py
app/streamlit_app.py
```

Validación local:

```text
DASHBOARD-01 DATA CONTRACT: PASS
team: Deportivo Alavés
matches: 38
players: 36
FEATURE-01 metrics available: 28
final engine: expert_0.7.0
decision rows: 154475
N13000 rows: 2505
Final recommendation gate safety: PASS
```

Streamlit arrancó correctamente en `localhost:8501`. TEAM / PLAYER / PARTITS están disponibles. La revisión visual final sigue abierta antes de cerrar formalmente DASHBOARD-01.

Los warnings `use_container_width` se han eliminado en la versión preparada para LLM-02 usando `width='stretch'`.

## 12. LLM

Arquitectura obligatoria: `DATA → ANALYTICS → DECISION ENGINE → LLM → COACH`.

### LLM-01 — CERRADO / VALIDADO

Contextos read-only TEAM / PLAYER / MATCH y asistente determinista con guardrails.

```text
LLM-01 ASSISTANT CONTRACT: PASS
team context matches: 38
team context squad: 36
match lineup rows: 23
unsupported ranking/recommendation question guardrail: PASS
N12000/N13000 provenance explanation: PASS
```

No recalcula métricas ni crea rankings/recomendaciones.

### LLM-02 — PREPARADO / PENDIENTE VALIDACIÓN LOCAL

Añadido `llm/openai_provider.py` y routing opcional a OpenAI.

Contrato:
- usa Responses API;
- `store=False`;
- model por defecto `gpt-5.6-luna`, configurable con `FPS_LLM_MODEL`;
- requiere `OPENAI_API_KEY` solo para modo generativo;
- sin clave funciona el fallback determinista;
- preguntas de ranking/recomendación se bloquean antes de cualquier llamada externa;
- el proveedor solo recibe el contexto estructurado ya calculado;
- datos del contexto se tratan como datos, no instrucciones;
- si falla el proveedor, vuelve al asistente determinista.

Archivos:

```text
llm/openai_provider.py
llm/validate_stage2.py
tests/test_openai_provider.py
```

La validación `llm/validate_stage2.py` no realiza ninguna llamada externa.

## 13. PDF

Pendiente. Será exportación estática de la web con datos calculados, gráficos y texto explicativo generado exclusivamente desde resultados estructurados.

## 14. Decisiones descartadas / restricciones vigentes

- No usar variables Opta solo porque existan.
- No duplicar pérdidas derivadas.
- No inferir formación ni rol sin evidencia.
- No crear role stints ficticios.
- No forzar eventos atómicos desde agregados ambiguos.
- No inventar umbrales GPS.
- No usar fuzzy matching silencioso GPS.
- No convertir dirección matemática en juicio de rendimiento sin regla validada por métrica.
- No mezclar historiales de roles distintos para evaluar encaje de rol.
- No fijar mínimo de muestra de rol por intuición.
- No etiquetar consistencia alta/baja o improving/declining sin validación.
- No interpretar conteos N12000 como score de fit.
- No emitir recomendación N13000 mientras la política final siga sin validar.
- El LLM no puede recalcular métricas críticas ni sobreescribir el motor analítico.
- Ninguna API key o secreto se sube al repositorio.

## 15. Problemas abiertos

- validar localmente LLM-02;
- confirmar visualmente TEAM / PLAYER / PARTITS / ASSISTENT y cerrar DASHBOARD-01;
- probar llamada generativa real solo cuando `OPENAI_API_KEY` esté configurada localmente;
- estudiar política futura de recomendación con literatura/datos/experimentos;
- añadir features físicas cuando haya GPS real o definiciones justificadas;
- script de anonimización para publicación;
- mejorar reejecución incremental;
- retocar UX Collector al final;
- localizar fuente fiable de `key_passes` si aparece otro export.

## 16. Siguiente paso exacto

```powershell
pip install -r requirements.txt
python llm\validate_stage2.py
streamlit run app\streamlit_app.py
```

Esperado: `LLM-02 PROVIDER ROUTING CONTRACT: PASS`.

Esta validación no hace ninguna llamada externa. Si después se configura `OPENAI_API_KEY` localmente, el modo Assistent podrá usar OpenAI manteniendo los mismos guardrails. No enviar la clave por chat ni subirla a GitHub.
