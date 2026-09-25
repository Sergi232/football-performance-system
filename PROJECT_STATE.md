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
EXPERT-01 N1000-N3000                    CERRADO / VALIDADO
EXPERT-02 N4000-N7000                    PREPARADO / PENDIENTE VALIDACIÓN LOCAL
Dashboard                                DESPUÉS DEL MOTOR
LLM / PDF                                DESPUÉS DEL DASHBOARD BASE
```

El Collector puede recibir mejoras visuales/UX posteriormente, pero su contrato de datos ya no bloquea el desarrollo.

## 2. Objetivo del producto

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

TEAM MODE es el producto principal. PLAYER MODE es complementario. RIVAL MODE queda como extensión futura y el sistema principal no depende de datos del rival.

## 3. Principios aprobados

- GPS es opcional y complementario.
- Separación estricta entre raw, features, modelos y conclusiones.
- Ninguna conclusión importante depende exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso debe justificarse con datos, literatura, validación o experimento.
- No rellenar datos ausentes mediante supuestos silenciosos.
- PannaData/Opta sirve para desarrollar y validar; no define la taxonomía del Collector amateur.
- Una estadística raw puede conservarse aunque su interpretación final requiera contexto.
- GitHub es la fuente de verdad técnica.
- Priorizar MVP funcional antes de aumentar complejidad.

## 4. Arquitectura materializada

```text
collector/       captura manual/vídeo y taxonomía
data/            esquema, imports y datos normalizados
gps/             contrato y normalización multi-proveedor
features/        variables derivadas deterministas y temporales
engine/          análisis determinista
decision_tree/   sistema experto auditable
models/          ML opcional
app/             dashboard web
llm/             consulta y explicación
reports/         exportación PDF
tests/           regresión y validación
```

Base: DuckDB. Unidad analítica principal: `player_match = jugador + partido`.

Tablas principales:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
player_match_raw_stats
collector_sessions
gps_imports
gps_player_map
gps_observations
player_match_features
decision_results
```

Versiones de esquema:

```text
0.1.0 core event-oriented schema
0.2.0 player_match_raw_stats
0.3.0 tackles_won + goals_conceded
0.4.0 GPS normalization contract
```

## 5. Caso demostrador

```text
Deportivo Alavés — LaLiga 2025/26
Opta team id: 4dtdjgnpdq9uw4sdutti0vaar
38 partidos
36 jugadores
835 player_match
```

Antes de publicar se anonimizará como TEAM_001 / PLAYER_001 / OPP_001 con IDs internos. Nunca se publicarán datasets completos originales de PannaData/Opta.

## 6. DATA — CERRADO

### DATA-01

- 38 fixtures.
- 590 player_match iniciales con participación.
- validación PASS.

### DATA-02

- 835 filas finales de `player_match`.
- 418 titulares = 38 x 11.
- 245 suplentes con 0 minutos incorporados desde lineups.
- 36 jugadores distintos.
- no se infiere formación desde `formation_place`.
- no se crean role stints ficticios.

### DATA-03

`opta_events.parquet` no es un feed atómico completo en este export. No se inventan pases, regates, tackles, intercepciones, faltas o pérdidas.

```text
shot_events fuente                    464
autogol excluido                        1
SHOT importados                        463
cobertura                            38/38
```

`shots_blocked` queda `AGGREGATE_CANONICAL`. Tarjetas: 98 importadas; 2 son eventos de equipo sin atribución de jugador y se guardan con `player_id=NULL`.

### DATA-04

`player_match_raw_stats`: 835/835 filas, 38/38 partidos, 36 jugadores. Validación PASS.

27 estadísticas raw aprobadas:

```text
passes_total
passes_completed
assists
long_balls_total
long_balls_completed
crosses_total
crosses_completed
dribbles_total
dribbles_won
turnovers
dispossessed
shots_total
shots_blocked
goals
tackles_total
tackles_won
interceptions
blocked_passes
clearances
fouls_committed
fouls_received
yellow_cards
red_cards
penalties_conceded
penalties_won
saves
goals_conceded
```

`key_passes` es útil para el sistema/Collector, pero este export no tiene una columna verificada equivalente. No se aproxima.

Los `NULL` de la fuente se preservan como `NULL`.

### Reparación de fecha de partido

FEATURE-02 detectó que `matches.match_date` estaba a NULL por parsing incorrecto del formato real de Opta.

```text
fuente: opta_fixtures.match_date
formato: YYYY-MM-DDZ
fixtures reparados: 38/38
distinct dates: 38
```

No se infirió cronología desde IDs ni orden de filas.

## 7. COLLECTOR-01 — CERRADO FUNCIONALMENTE

Catálogo: `collector/event_catalog.json` v0.3.0.

Acciones MVP:

```text
PASS NORMAL/LONG/CROSS → SUCCESS/FAIL
DRIBBLE → SUCCESS/FAIL
SHOT → GOAL/ON_TARGET/OFF_TARGET/BLOCKED
TACKLE → SUCCESS/FAIL
INTERCEPTION
BLOCK
CLEARANCE
FOUL COMMITTED/RECEIVED
CARD YELLOW/RED
LOSS OTHER
PENALTY WON/CONCEDED → GOAL/MISSED
CORNER FOR/AGAINST
GK SAVE/GOAL_CONCEDED
```

Qualifiers: `key_pass`, `assist`, `second_yellow`, `set_piece_result`, `penalty_taker_player_id`.

Decisiones clave:

- LONG/CROSS cuentan también como pase total.
- PASS FAIL y DRIBBLE FAIL generan pérdida derivada.
- LOSS se reserva para otras pérdidas.
- poste agrupado en OFF_TARGET en MVP.
- falta peligrosa no es un botón subjetivo: se captura x/y y se derivará cuando exista criterio validado.
- córners/faltas conservan tiempo de partido/vídeo para clips ABP.

Versión funcional: `collector/data_collector_futbol_mvp.html`.

Validación local: PASS, 20/20 acciones cubiertas. Retocs visuales/UX quedan en backlog no bloqueante.

## 8. GPS-01 — CERRADO / VALIDADO

Contrato normalizado multi-proveedor en `gps/`.

Unidades canónicas:

```text
timestamp_ms      milisegundos
distance_m        metros
speed_m_s         m/s
acceleration_m_s2 m/s²
x/y               metros cuando el mapping espacial es seguro
```

Incluye mapping declarativo, conversión de unidades, distancia acumulada→incremental, `gps_player_map`, metadatos de importación y controles de calidad. No hay fuzzy matching silencioso ni umbrales inventados de sprint/HIE/carga.

Validación local: `GPS-01 VALIDATION: PASS`.

## 9. FEATURE-01 — CERRADO / VALIDADO

Catálogo: `features/catalog.json` v0.1.0.

28 features deterministas:

- 7 ratios de efectividad;
- 21 variables por 90 minutos.

Reglas:

- ratio solo si numerador/denominador existen y denominador > 0;
- por90 solo si `minutes_played > 0`;
- NULL raw permanece NULL;
- sin ratings, pesos, percentiles ni umbrales expertos.

Validación local 25/09/2026:

```text
FEATURE-01 VALIDATION: PASS
feature rows: 23380/23380
non-null values: 6324
coverage: 38 matches / 36 players
ratio domains [0,1]: PASS
per-90 + zero-minute NULL: PASS
raw NULL preservation: PASS
```

## 10. FEATURE-02 — CERRADO / VALIDADO

Catálogo: `features/temporal_catalog.json` v0.2.0.

Para cada una de las 28 features base se crean 7 primitivas temporales:

```text
history_n
prev
prior_mean
prior_std
delta_prev
delta_prior_mean
prior_slope
```

Contrato anti-leakage:

- solo usa observaciones con `match_date` estrictamente anterior;
- el partido actual nunca entra en su propio baseline;
- partidos de la misma fecha no se informan entre sí;
- futuros nunca entran;
- NULL no se convierte a cero;
- no hay ventanas arbitrarias 3/5/10.

Validación local 25/09/2026:

```text
FEATURE-02 VALIDATION: PASS
feature_version: 0.2.0
base features: 28
temporal operators: 7
feature rows: 163660/163660
coverage: 38 matches / 36 players
history_n integer/non-negative: PASS
prior_std non-negative: PASS
first-date strict-past contract: PASS
```

## 11. Sistema experto

Arquitectura prevista:

```text
N1000  disponibilidad / actividad
N2000  perfil estructural
N3000  forma / evolución
N4000  amenaza ofensiva
N5000  creación / progresión
N6000  contribución defensiva
N7000  finalización
N8000  contexto del equipo
N9000  componente físico
N10000 rol y encaje táctico
N11000 consistencia / tendencia
N12000 player fit
N13000 recomendación final
```

Cada nodo mantiene:

```text
entrada → condición → resultado → confianza → justificación
```

### EXPERT-01 — CERRADO / VALIDADO

Motor: `expert_0.1.0`.

Archivos:

```text
decision_tree/catalog.json
decision_tree/build_stage1.py
decision_tree/validate_stage1.py
decision_tree/run_stage1.py
tests/test_decision_tree_stage1.py
```

Nodos:

- `N1000.100`: actividad/listado observada desde minutos + titularidad; no infiere lesión ni disponibilidad médica.
- `N2000.100`: rol estructural observado; no infiere arquetipo ni player-fit.
- `N3000.*.DELTA_PRIOR_MEAN`: valor actual frente a media strict-past.
- `N3000.*.PRIOR_SLOPE`: dirección matemática de la pendiente strict-past.

Validación local 25/09/2026:

```text
EXPERT-01 VALIDATION: PASS
engine_version: expert_0.1.0
player_match rows: 835
base features: 28
decision rows: 48430/48430
family coverage: N1000=835, N2000=835, N3000=46760
duplicate node outputs: 0
deterministic confidence contract: PASS
no premature good/bad/improving/declining/recommendation labels: PASS
```

`confidence=1.0` significa ejecución determinista de la regla, no probabilidad calibrada de rendimiento.

La frontera 0 describe únicamente el signo matemático. `ABOVE_PRIOR_MEAN` no equivale automáticamente a “mejor”.

### EXPERT-02 — PREPARADO / PENDIENTE VALIDACIÓN LOCAL

Motor: `expert_0.2.0`.

Archivos:

```text
decision_tree/domain_catalog.json
decision_tree/build_stage2.py
decision_tree/validate_stage2.py
decision_tree/run_stage2.py
tests/test_decision_tree_stage2.py
```

Diseño:

- N1000-N3000 se arrastran exactamente desde `expert_0.1.0`.
- N4000 añade evidencia de amenaza ofensiva.
- N5000 añade creación/progresión y costes de pérdida.
- N6000 añade contribución defensiva y costes disciplinarios defensivos.
- N7000 añade output y contexto de finalización.
- cada señal se compara únicamente con el historial strict-past del mismo jugador.
- `metric_role = volume/output/efficiency/cost/context` es metadata semántica, no un peso.
- no hay scores, pesos, percentiles, ajuste por rol, recomendaciones ni umbrales de significancia práctica.
- la escritura en DuckDB se hace en bloque para evitar el cuello de botella de `executemany` observado en EXPERT-01.

## 12. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica y consulta resultados estructurados. No inventa métricas ni sustituye cálculos críticos.

## 13. Decisiones descartadas / restricciones

- No usar todas las variables Opta solo porque existan.
- No duplicar pérdidas derivadas.
- No inferir formación sin evidencia.
- No crear role stints ficticios.
- No forzar semántica event-level desde agregados ambiguos.
- No tratar `opta_events` como feed atómico completo.
- No hacer que una estadística raw positiva cambie automáticamente los minutos.
- No inventar umbrales GPS de sprint/HIE/carga antes de justificarlos.
- No usar fuzzy matching silencioso para identidades GPS.
- No convertir métricas propietarias GPS en features canónicas automáticamente.
- No convertir la dirección matemática de N3000-N7000 en juicio de rendimiento sin una regla validada por métrica.
- No usar un score global ni recomendación final antes de validar reglas y pesos.

## 14. Problemas abiertos

- validar localmente EXPERT-02;
- diseñar después N8000 contexto del equipo con variables realmente disponibles;
- N9000 debe funcionar como rama opcional cuando no haya GPS;
- decidir reglas de muestra mínima/significancia práctica con validación, no por intuición;
- añadir features físicas de rendimiento cuando exista GPS real o definición suficientemente justificada;
- crear script de anonimización para publicación;
- mejorar reejecución incremental de algunos imports;
- retocar UX del Collector al final;
- determinar fuente fiable de `key_passes` si aparece otro export.

## 15. Siguiente paso exacto

Ejecutar:

```powershell
python decision_tree\run_stage2.py
```

Si pasa:

1. cerrar EXPERT-02;
2. construir N8000 contexto del equipo sin depender del rival;
3. diseñar N9000 como rama física opcional y degradable cuando GPS no exista;
4. preparar N10000 rol/encaje utilizando primero evidencia auditable antes de cualquier score o recomendación.
