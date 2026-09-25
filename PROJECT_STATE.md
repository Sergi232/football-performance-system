# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto y prevalece sobre conversaciones antiguas cuando exista contradicción.

## 1. Fase actual

**Track A — DATA base del MVP estabilizada. Track B — cerrar Data Collector antes de GPS/Feature Engine.**

```text
arquitectura                         HECHO
esquema DuckDB + migraciones         HECHO
auditoría fuentes reales             HECHO
DATA-01 fixtures + player_match      CERRADO / VALIDADO
DATA-02 lineups + titularidad/rol    CERRADO / VALIDADO
DATA-03 events + shots               CERRADO / VALIDADO LOCALMENTE
DATA-04 player stats agregados       CERRADO / VALIDADO LOCALMENTE
Collector MVP                        SIGUIENTE
GPS normalizado                      DESPUÉS DE COLLECTOR
Feature Engine                       DESPUÉS DE DATA + GPS BASE
Sistema experto                      DESPUÉS DE FEATURES
Dashboard / LLM / PDF                DESPUÉS
```

La base está orientada a eventos, pero no se fuerza a que todas las métricas procedan de eventos atómicos. Cada métrica usa la fuente canónica más fiable disponible.

## 2. Objetivo confirmado

Desarrollar una aplicación web funcional para equipos de fútbol amateur o semiprofesional sin departamento de análisis propio.

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

La web es el producto principal. Los PDF son exportaciones estáticas.

## 3. Principios aprobados

- Team Mode es principal; Player Mode complementario; Rival Mode extensión futura.
- El sistema principal debe funcionar sin datos del rival.
- GPS es complementario, no obligatorio.
- Separación estricta entre datos brutos, features, modelos y conclusiones.
- Ninguna conclusión importante depende exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso debe justificarse con datos, literatura, validación o experimento.
- Priorizar MVP funcional antes de aumentar complejidad.
- GitHub es la fuente de verdad técnica.
- Documentación oficial del repositorio/TFM en castellano.
- Código y nombres técnicos pueden estar en inglés.
- No completar datos ausentes con supuestos silenciosos.
- Si una fuente no permite conocer una variable, queda `NULL`, se conserva como agregado o se marca como no reconstruible.
- El caso demostrador usa datos reales y se anonimizará antes de publicarse.
- PannaData/Opta sirve para desarrollar y validar el sistema; no dicta la taxonomía del Collector amateur.
- Una estadística raw disponible puede conservarse aunque su interpretación analítica final todavía requiera contexto; raw no equivale a feature ni a conclusión.

## 4. Arquitectura materializada

```text
collector/       captura y taxonomía de eventos
data/            esquema, imports y dataset normalizado
gps/             normalización multi-proveedor
features/        variables derivadas
engine/          análisis determinista
decision_tree/   sistema experto auditable
models/          ML opcional
app/             dashboard web
llm/             consulta y explicación
reports/         PDF
tests/           tests de datos/lógica/regresión
```

Documento principal: `docs/ARCHITECTURE.md`.

## 5. Base de datos

Motor: **DuckDB**.

Unidad analítica principal:

```text
player_match = jugador + partido
```

Tablas principales actuales:

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
gps_observations
player_match_features
decision_results
```

Versiones de esquema aplicadas localmente:

```text
0.1.0 core event-oriented schema
0.2.0 player_match_raw_stats
0.3.0 expand raw stats: tackles_won + goals_conceded
```

### match_events

```text
match + team + player nullable
action_type + subtype + outcome
period + match_second + video_second
x + y
qualifiers
linked_event_id
source_type + source_event_id
```

`player_id` puede ser `NULL` para un evento real de equipo cuando la fuente no identifica al jugador. No se inventa una atribución.

### player_match_raw_stats

Capa raw/agregada separada de `player_match_features`. Conserva valores de proveedor y `NULL` de fuente; no guarda porcentajes ni métricas derivadas.

Regla de pérdidas de eventos:

```text
PASS | ... | FAIL  → FAILED_PASS
DRIBBLE | FAIL     → FAILED_DRIBBLE
LOSS               → OTHER_TURNOVER / subtipo
```

No debe existir doble conteo de pérdidas.

## 6. Fuentes reales PannaData/Opta

Ruta local:

```text
C:\Users\sergi\Desktop\analisi_futbol\input\pannadata\
```

Auditoría 25/09/2026:

```text
opta_fixtures.parquet       243.562 filas / 13 columnas
opta_lineups.parquet      8.850.866 filas / 17 columnas
opta_player_stats.parquet 8.915.362 filas / 288 columnas
opta_players.parquet        263.236 filas / 14 columnas
opta_events.parquet       4.087.160 filas / 15 columnas
opta_shot_events.parquet  3.305.837 filas / 23 columnas
opta_shots.parquet        1.604.338 filas / 29 columnas
opta_match_xg.parquet       106.538 filas / 3 columnas
```

Caso demostrador:

```text
Deportivo Alavés — LaLiga 2025/26
Opta team id: 4dtdjgnpdq9uw4sdutti0vaar
38 partidos
```

## 7. DATA-01 — CERRADO / VALIDADO

### Fixtures

```text
38 fixtures
38 partidos distintos
0 duplicados source_match_id
0 rivales ausentes
VALIDATION PASS
```

### Participación inicial

```text
590 player_match con participación
38/38 partidos
28 jugadores distintos
245 filas con minsPlayed nulo excluidas inicialmente
0 minutos inválidos
VALIDATION PASS
```

Los minutos nulos no se convirtieron en 0. La participación completa se resolvió posteriormente con `opta_lineups`.

Ejecución limpia:

```bash
python data/run_stage2.py --reset
```

El `--reset` existe por una limitación de DuckDB al hacer upsert de filas padre referenciadas por foreign keys. La reejecución incremental sin reset sigue siendo una mejora técnica futura.

## 8. DATA-02 — CERRADO / VALIDADO

Fuente: `opta_lineups.parquet`.

```text
filas lineup fuente                 835
filas existentes enriquecidas       590
suplentes 0 minutos insertados       245
player_match finales                 835
cobertura                            38/38
starters                             418 = 38 x 11
jugadores distintos                   36
roles fuente de titulares escritos  418
starting_formation                    0/38
```

Decisiones:

- `is_starter` es la fuente de titularidad.
- `minutes_played = 0` permite incorporar suplentes no utilizados.
- Para titulares, `primary_role` usa solo `position` + `position_side` observados.
- `position='Substitute'` no se convierte en rol táctico.
- `formation_place` no se usa para inventar una formación.
- `team_match.starting_formation` queda `NULL`: la fuente no trae formación explícita.
- No se crean `player_role_stints`: la fuente no permite reconstruir cambios de rol de forma fiable.

Archivos:

```text
data/inspect_demo_lineups.py
data/import_demo_lineups.py
data/run_stage2b.py
tests/test_lineup_import.py
```

## 9. DATA-03 — CERRADO / VALIDADO LOCALMENTE

Fuentes:

```text
opta_events.parquet
opta_shot_events.parquet
opta_shots.parquet
```

### Hallazgo estructural

`opta_events.parquet` en este export no es un feed atómico completo. En los 38 partidos del demostrador solo contiene:

```text
substitution
yellow_card
second_yellow
goal
```

No se inventan eventos atómicos de pase, regate, entrada, intercepción, despeje, falta o pérdida.

### Remates

```text
shot_events fuente                         464
autogoles excluidos de SHOT atacante         1
SHOT normalizados/importados               463
cobertura                                  38/38

BLOCKED                                    126
GOAL                                        41
OFF_TARGET                                 186
ON_TARGET                                  110
```

Contrato validado:

```text
total_shots mismatches                       0
shots_off_target mismatches                   0
goals mismatches                              0
shots_penalty mismatches                      0
shots_on_target bound mismatches              0
on_target + blocked partition mismatches      0
shots_blocked                    AGGREGATE_CANONICAL
```

Decisiones:

- El outcome Collector sigue siendo exclusivo `GOAL / ON_TARGET / OFF_TARGET / BLOCKED`.
- `opta_shots.shots_on_target` y `shots_blocked` son agregados canónicos cuando no pueden atribuirse sin adivinar a un event concreto.
- `opta_shot_events.is_blocked` se conserva como evidencia del evento.
- Los goles de `opta_events` no se importan para evitar doble conteo.

### Tarjetas

```text
CARD importadas                              98
CARD de equipo sin jugador normalizado        2
source player missing                         2
source player id unresolved                   0
```

Las dos tarjetas sin jugador se guardan con `player_id=NULL`.

### Validación final

```text
38/38 partidos
0 orphan match_events
0 duplicate source events
VALIDATION STATUS PASS
```

Archivos:

```text
data/inspect_demo_events.py
data/import_demo_events_contract_v2.py
data/run_stage3a.py
tests/test_event_source_contract.py
```

## 10. DATA-04 — CERRADO / VALIDADO LOCALMENTE

Fuente: `opta_player_stats.parquet`.

Inspección real:

```text
filas demo                835
partidos                 38/38
jugadores distintos        36
columnas fuente            288
```

### Raw stats incorporadas

```text
passes_total              <- totalPass
passes_completed          <- accuratePass
assists                   <- goalAssist
long_balls_total          <- totalLongBalls
long_balls_completed      <- accurateLongBalls
crosses_total             <- totalCross
crosses_completed         <- accurateCross
dribbles_total            <- totalContest
dribbles_won              <- wonContest
turnovers                 <- turnover
dispossessed              <- dispossessed
shots_total               <- totalScoringAtt
shots_blocked             <- blockedScoringAtt
goals                     <- goals
tackles_total             <- totalTackle
tackles_won               <- wonTackle
interceptions             <- interception
blocked_passes            <- blockedPass
clearances                <- totalClearance
fouls_committed           <- fouls
fouls_received            <- wasFouled
yellow_cards              <- yellowCard
red_cards                 <- redCard
penalties_conceded        <- penaltyConceded
penalties_won             <- penaltyWon
saves                     <- saves
goals_conceded            <- goalsConceded
```

Total: **27 estadísticas raw**.

`key_passes` sigue como variable útil del sistema/Collector, pero este export concreto no tiene una columna verificada equivalente. No se rellena con otra estadística por aproximación.

`divingSave` existe en Opta, pero no se incorpora como variable principal porque `saves` cubre la acción de porter aprobada para el MVP.

### Resultado Stage 4 v2

```text
source/imported rows                     835/835
coverage                                  38/38
distinct players                             36
source/player_match minute alignment       PASS
non-negative/integer constraints           PASS
subset constraints                         PASS
DATA-03 shots_total/goals cross-check      PASS
tackles_won imported sum                    402
goals_conceded imported sum                 612
source NULL values preserved               PASS
DATABASE VALIDATION STATUS                 PASS
```

### Caso 0 minutos + estadística positiva

Existe exactamente una fila con 0 minutos según lineups que contiene una `yellow_card` positiva en `opta_player_stats`:

```text
match source id:  36vy9cu402k8m0goxchkpmpzo
player source id: 2ww626a9v31b072prdx0xf1g4
raw stat:         yellow_cards
```

Decisión: se preserva la estadística raw y se audita, pero **no modifica la participación**. Los minutos de `opta_lineups` siguen siendo la fuente canónica de participación. Una tarjeta puede existir para un jugador del banquillo sin implicar minutos jugados.

Archivos:

```text
data/inspect_demo_player_stats.py
data/import_demo_player_match_stats_v2.py
data/migrations/002_player_match_raw_stats.sql
data/migrations/003_expand_raw_stats.sql
data/run_stage4.py
tests/test_player_match_raw_stats.py
```

## 11. Data Collector — estado actual

Catálogo: `collector/event_catalog.json` versión 0.2.0.

Aprobado:

```text
PASS | NORMAL | SUCCESS/FAIL
PASS | LONG   | SUCCESS/FAIL
PASS | CROSS  | SUCCESS/FAIL
DRIBBLE | SUCCESS/FAIL
SHOT | GOAL / ON_TARGET / OFF_TARGET / BLOCKED
TACKLE | SUCCESS/FAIL
INTERCEPTION
BLOCK
CLEARANCE
FOUL | COMMITTED
FOUL | RECEIVED
CARD | YELLOW
CARD | RED
LOSS | OTHER
GK | SAVE
GK | GOAL_CONCEDED
```

Reglas:

- `LONG` y `CROSS` cuentan automáticamente como pases totales.
- `PASS FAIL` y `DRIBBLE FAIL` generan pérdida derivada.
- `LOSS` solo para pérdidas no explicadas por pase/regate fallado.
- Poste se agrupa en `OFF_TARGET` para el MVP.
- Cada `TACKLE` cuenta para `tackles_total`; `TACKLE SUCCESS` cuenta para `tackles_won`.

Parcial:

```text
PENALTY → WON / CONCEDED → GOAL / MISSED
```

Pendiente de cerrar:

- definición operativa de falta peligrosa;
- confirmar `CORNER | FOR/AGAINST`;
- decidir resultado de ABP solo si es reproducible y útil;
- cerrar interfaz exacta de penalti;
- simplificar el HTML actual contra el catálogo definitivo.

Acciones mínimas de portero ya cerradas: `SAVE` y `GOAL_CONCEDED`.

## 12. Anonimización

Antes de publicar:

```text
Deportivo Alavés → TEAM_001
jugadores         → PLAYER_001, PLAYER_002, ...
oponentes         → OPP_001, OPP_002, ...
IDs originales    → IDs internos
```

Nunca se publicarán datasets completos originales de PannaData/Opta.

Script previsto: `scripts/build_anonymized_demo.py`.

## 13. GPS — pendiente

GPS es opcional y complementario. La capa de base ya existe (`gps_imports`, `gps_observations`), pero falta cerrar el contrato multi-proveedor.

Variables raw candidatas:

```text
timestamp
posición x/y
distancia
velocidad
aceleración/desaceleración
```

Los esfuerzos de alta intensidad y otras métricas avanzadas deben derivarse posteriormente; no se capturan manualmente.

## 14. Sistema experto previsto

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

Cada nodo:

```text
entrada → condición → resultado → confianza → justificación
```

No se detallan ramas hasta estabilizar DATA + Feature Engine.

## 15. LLM

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados calculados; no inventa métricas ni sustituye cálculos críticos.

## 16. Tests y GitHub Actions

Tests actuales:

```text
tests/test_data_pipeline.py
tests/test_lineup_import.py
tests/test_event_source_contract.py
tests/test_player_match_raw_stats.py
```

Durante desarrollo, `.github/workflows/tests.yml` es manual (`workflow_dispatch`) para evitar emails repetitivos por cada push. Antes de publicar se reactivarán `push` y `pull_request` y se dejará CI verde.

La validación con datos reales locales tiene prioridad sobre un test sintético.

## 17. Decisiones descartadas / no aprobadas

- No usar todas las variables Opta solo porque existan.
- No construir todavía el árbol experto detallado.
- No construir Feature Engine definitivo sobre DATA no estable.
- No publicar datasets completos de PannaData/Opta.
- No duplicar pérdidas derivadas de pase/regate fallado.
- No crear botón separado para remate al poste.
- No convertir minutos nulos en 0 sin evidencia.
- No inferir formación a partir de `formation_place` sin regla validada.
- No crear role stints si la fuente no permite reconstruir cambios de rol.
- No inventar mappings de outcomes/qualifiers.
- No forzar `shots_on_target` o `shots_blocked` agregados a un evento concreto cuando la fuente no permite identificarlo.
- No usar `opta_events` como si fuera un feed atómico completo.
- No descartar una estadística raw del sistema solo porque necesite interpretación posterior; se conserva separada de features cuando la fuente está identificada.
- No hacer que una estadística raw positiva de un suplente cambie automáticamente sus minutos de participación.

## 18. Problemas abiertos

- Cerrar falta peligrosa/córners/ABP/penalti en Collector.
- Simplificar el HTML del Collector definitivo.
- Definir normalización GPS multi-proveedor.
- Crear anonimización.
- Mejorar reejecución incremental sin depender de `--reset`.
- Construir Feature Engine cuando Collector + contrato GPS base estén cerrados.
- Determinar fuente de `key_passes` si se dispone de otro export; mientras tanto queda ausente en este demostrador.

## 19. Siguiente paso exacto

Cerrar **COLLECTOR-01** usando el HTML existente y `collector/event_catalog.json` como base:

1. decidir `CORNER | FOR/AGAINST`;
2. definir criterio reproducible de falta peligrosa;
3. decidir si `set_piece_result` entra en MVP;
4. cerrar flujo de penalti;
5. simplificar el HTML sin añadir variables no aprobadas.

Después: definir contrato GPS multi-proveedor y pasar al Feature Engine.
