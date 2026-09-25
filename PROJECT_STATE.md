# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto y prevalece sobre conversaciones antiguas cuando exista contradicción.

## 1. Fase actual

**Track A — DATA en implementación activa. Track B — Data Collector en paralelo.**

```text
arquitectura                         HECHO
esquema DuckDB v0.1                  HECHO
auditoría fuentes reales             HECHO
DATA-01 fixtures + player_match      CERRADO / VALIDADO
DATA-02 lineups + titularidad/rol    CERRADO / VALIDADO
DATA-03 events + shots               CERRADO / VALIDADO LOCALMENTE
DATA-04 player stats agregados       SIGUIENTE
Collector MVP                        EN PARALELO
Feature Engine                       DESPUÉS DE ESTABILIZAR DATA
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

Tablas principales:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
collector_sessions
gps_imports
gps_observations
player_match_features
decision_results
```

`match_events` mantiene:

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

Regla de pérdidas:

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

### Participación inicial desde `opta_player_stats`

```text
590 player_match con participación
38/38 partidos
28 jugadores distintos
245 filas con minsPlayed nulo excluidas
0 minutos inválidos
VALIDATION PASS
```

Los minutos nulos no se convierten en 0. La participación completa se resolvió posteriormente con `opta_lineups`.

Ejecución limpia:

```bash
python data/run_stage2.py --reset
```

El `--reset` existe por una limitación de DuckDB al hacer upsert de filas padre referenciadas por foreign keys. La reejecución incremental sin reset sigue siendo una mejora técnica futura, no una garantía actual.

## 8. DATA-02 — CERRADO / VALIDADO

Fuente: `opta_lineups.parquet`.

Resultado:

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

Archivos principales:

```text
data/inspect_demo_lineups.py
data/import_demo_lineups.py
data/run_stage2b.py
tests/test_lineup_import.py
```

## 9. DATA-03 — CERRADO / VALIDADO LOCALMENTE

Fuentes inspeccionadas:

```text
opta_events.parquet
opta_shot_events.parquet
opta_shots.parquet
```

### Hallazgo estructural clave

`opta_events.parquet` en este export no es un feed atómico completo. Para los 38 partidos del demostrador contiene únicamente eventos resumen de:

```text
substitution
yellow_card
second_yellow
goal
```

Por tanto, no contiene eventos atómicos de pase, regate, entrada, intercepción, despeje, falta o pérdida. Esas acciones **no se inventan** y se obtendrán de agregados `opta_player_stats` o del Collector.

### Remates

`opta_shot_events.parquet` sí contiene eventos atómicos de remate con `event_id`, jugador, minuto/segundo, coordenadas, tipo, cuerpo, situación, xG/xGOT y flags de gol/bloqueo.

Resultado real Stage 3A:

```text
shot_events fuente                         464
autogoles excluidos de SHOT atacante         1
SHOT normalizados/importados               463
cobertura                                  38/38

outcomes Collector-facing:
BLOCKED                                    126
GOAL                                        41
OFF_TARGET                                 186
ON_TARGET                                  110
```

Validación del contrato de fuentes:

```text
total_shots mismatches                       0
shots_off_target mismatches                   0
goals mismatches                              0
shots_penalty mismatches                      0
shots_on_target bound mismatches              0
on_target + blocked partition mismatches      0
shots_blocked                    AGGREGATE_CANONICAL
```

Decisión metodológica:

- El `outcome` del Collector sigue siendo exclusivo: `GOAL / ON_TARGET / OFF_TARGET / BLOCKED`.
- `opta_shots.shots_on_target` y `shots_blocked` se consideran métricas agregadas canónicas cuando la identidad exacta del evento no puede recuperarse sin adivinar.
- `opta_shot_events.is_blocked` se conserva como evidencia del evento, pero no se fuerza a reproducir `shots_blocked` agregado uno a uno.
- Los agregados se usan para validar compatibilidad, no para asignar arbitrariamente una categoría a un remate concreto.
- `source_event_id` real se conserva para los shot events.
- Los goles de `opta_events` no se importan para evitar doble conteo con `opta_shot_events`.

### Tarjetas

Resultado:

```text
CARD importadas                              98
CARD de equipo sin jugador normalizado        2
source player missing                         2
source player id unresolved                   0
```

Las dos tarjetas sin jugador se guardan como eventos de equipo (`player_id=NULL`) y se conserva en `qualifiers` que la atribución no estaba disponible en la fuente.

### Validación final de base

```text
demo_team_exists             OK
demo_match_count             38/38
duplicate_source_match_ids   0
missing_opponents            0
player_match_rows_present    OK
match_event_rows_present     OK
player_match_fixture_coverage 38/38
invalid_minutes              0
orphan_match_events          0
duplicate_source_events      0
VALIDATION STATUS            PASS
```

Archivos principales:

```text
data/inspect_demo_events.py
data/import_demo_events_contract_v2.py
data/run_stage3a.py
```

## 10. DATA-04 — SIGUIENTE

Objetivo: auditar y normalizar las estadísticas agregadas jugador-partido de `opta_player_stats.parquet` que sí corresponden a variables aprobadas o candidatas del Collector.

Variables a verificar en la fuente real:

```text
pases totales / completados
pases clave / asistencias
pases largos totales / completados
centros totales / completados
regates totales / ganados
pérdidas / dispossessions
remates agregados de control
tackles / tackles ganados
intercepciones
bloqueos
despejes
faltas cometidas / recibidas
tarjetas
penalti ganado / concedido
paradas / goles encajados
```

Regla: estos datos son **raw/agregados de fuente**, no features derivadas. No deben mezclarse silenciosamente con `player_match_features`.

Inspector previsto/creado: `data/inspect_demo_player_stats.py`.

## 11. Data Collector — variables aprobadas

```text
PASS | NORMAL | SUCCESS/FAIL
PASS | LONG   | SUCCESS/FAIL
PASS | CROSS  | SUCCESS/FAIL
DRIBBLE | SUCCESS/FAIL
SHOT | GOAL
SHOT | ON_TARGET
SHOT | OFF_TARGET
SHOT | BLOCKED
TACKLE
INTERCEPTION
BLOCK
CLEARANCE
FOUL | COMMITTED
FOUL | RECEIVED
CARD | YELLOW
CARD | RED
LOSS | OTHER
```

Reglas:

- `LONG` y `CROSS` cuentan automáticamente como pases totales.
- `PASS FAIL` y `DRIBBLE FAIL` generan pérdida derivada.
- `LOSS` solo para pérdidas no explicadas por pase/regate fallado.
- Poste se agrupa en `OFF_TARGET` para el MVP.

Parcial:

```text
PENALTY → WON / CONCEDED → GOAL / MISSED
```

Pendiente del Collector:

- definición operativa de falta peligrosa;
- confirmar `CORNER | FOR/AGAINST`;
- decidir resultado de ABP solo si es reproducible y útil;
- interfaz exacta de portero.

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

## 13. Sistema experto previsto

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

## 14. LLM

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados calculados; no inventa métricas ni sustituye cálculos críticos.

## 15. Tests y GitHub Actions

Tests actuales:

```text
tests/test_data_pipeline.py
tests/test_lineup_import.py
tests/test_event_source_contract.py
```

Durante desarrollo, `.github/workflows/tests.yml` es manual (`workflow_dispatch`) para evitar emails repetitivos por cada push. Antes de publicar se reactivarán `push` y `pull_request` y se dejará CI verde.

La validación con datos reales locales tiene prioridad sobre un test sintético.

## 16. Decisiones descartadas / no aprobadas

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
- No usar `opta_events` como si fuera un feed atómico completo: el export inspeccionado no lo es.

## 17. Problemas abiertos

- DATA-04: cerrar mapping real de agregados `opta_player_stats`.
- Definir dónde persistir raw stats agregados sin mezclarlos con features derivadas.
- Cerrar falta peligrosa/córners/ABP/portero en Collector.
- Crear anonimización.
- Definir normalización GPS.
- Mejorar reejecución incremental sin depender de `--reset`.
- Construir Feature Engine cuando DATA esté estable.

## 18. Siguiente paso exacto

Ejecutar:

```bash
python data/inspect_demo_player_stats.py
```

La salida debe confirmar qué columnas reales soportan las variables del Collector antes de diseñar su persistencia final.
