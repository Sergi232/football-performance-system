# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto y prevalece sobre conversaciones antiguas cuando exista contradicción.

## 1. Fase actual

**Track A — DATA en implementación activa. Track B — Data Collector en paralelo.**

Estado operativo:

```text
arquitectura                         HECHO
esquema DuckDB v0.1                  HECHO
auditoría fuentes reales             HECHO
DATA-01 fixtures + player_match      CERRADO / VALIDADO
DATA-02 lineups + titularidad/rol    VALIDADO LOCALMENTE
DATA-03 events + shots               SIGUIENTE
Collector MVP                        EN PARALELO
Feature Engine                       DESPUÉS DE ESTABILIZAR DATA
Sistema experto                      DESPUÉS DE FEATURES
Dashboard / LLM / PDF                DESPUÉS
```

La base está orientada a eventos. Decisiones pendientes del Collector como `CORNER`, falta peligrosa o resultado de ABP no bloquean la infraestructura DATA.

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
- Si una fuente no permite conocer una variable, queda `NULL` o pendiente.
- El caso demostrador usa datos reales y se anonimizará antes de publicarse.

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

Tabla estable de eventos:

```text
match_events
match + team + player
action_type + subtype + outcome
period + match_second + video_second
x + y
qualifiers
linked_event_id
source_type + source_event_id
```

Regla derivada ya implementada:

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

Auditoría real 25/09/2026:

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

## 7. DATA-01 — VALIDADO

### Stage 1 — fixtures

Mapping real:

```text
match_id         -> match_id
match_date       -> match_date
home_team_id     -> home_team_id
away_team_id     -> away_team_id
home_team_name   -> home_team
away_team_name   -> away_team
home_score       -> home_score
away_score       -> away_score
competition      -> competition
season           -> season
```

Resultado:

```text
38 fixtures
38 partidos distintos
0 duplicados source_match_id
0 rivales ausentes
VALIDATION PASS
```

El primer prototipo mezclaba 424 partidos porque detectaba `season` y `competition` pero no aplicaba correctamente esos filtros. Corregido.

### Stage 2A — players + player_match

Mapping real:

```text
match_id         -> match_id
team_id          -> team_id
player_id        -> player_id
player_name      -> player_name
minutes          -> minsPlayed
position         -> position
started          -> None
shirt_number     -> shirt_number
```

Resultado:

```text
590 player_match con participación
38/38 partidos
28 jugadores distintos
245 filas con minsPlayed nulo excluidas
0 minutos inválidos
VALIDATION PASS
```

Decisión: minutos nulos de `opta_player_stats` no se convierten en 0. La participación se resuelve con `opta_lineups`.

Ejecución limpia:

```bash
python data/run_stage2.py --reset
```

`--reset` borra únicamente la DuckDB generada y la reconstruye desde los Parquet originales.

## 8. DATA-02 — VALIDADO LOCALMENTE

Fuente inspeccionada: `opta_lineups.parquet`.

Esquema real relevante:

```text
match_id
match_date
player_id
player_name
team_id
team_name
team_position
position
position_side
formation_place
shirt_number
is_starter
minutes_played
sub_on_minute
sub_off_minute
competition
season
```

Resultado real del importador:

```text
filas lineup fuente                 835
filas existentes enriquecidas       590
suplentes 0 minutos insertados       245
player_match finales                 835
cobertura                            38/38
starters                             418 = 38 x 11
suplentes                            417
jugadores distintos                   36
roles fuente de titulares escritos  418
starting_formation                    0/38
```

Decisiones DATA-02:

- `is_starter` es la fuente de titularidad.
- `minutes_played = 0` en lineups permite incorporar de forma verificada suplentes no utilizados.
- Para titulares, `primary_role` usa únicamente `position` + `position_side` observados.
- Para suplentes, `position='Substitute'` no se convierte en un rol inventado; se mantiene el rol previo si existe.
- `formation_place` se conserva como evidencia disponible, pero **no se usa para inventar una formación de equipo**.
- La fuente inspeccionada no tiene columna explícita de formación; `team_match.starting_formation` queda `NULL`.
- No se crean `player_role_stints`: lineups no permite reconstruir cambios de rol con suficiente fiabilidad.

Archivos:

```text
data/inspect_demo_lineups.py
data/import_demo_lineups.py
data/run_stage2b.py
tests/test_lineup_import.py
```

## 9. DATA-03 — SIGUIENTE

Objetivo: mapear `opta_events.parquet`, `opta_shot_events.parquet` y `opta_shots.parquet` a `match_events` sin inventar outcomes ni qualifiers.

Inspector preparado:

```text
data/inspect_demo_events.py
```

Debe determinar con datos reales:

- columnas de `match_id`, `team_id`, `player_id`, `event_id`;
- `type_id` / tipo de evento;
- outcome;
- periodo y tiempo;
- coordenadas;
- qualifiers;
- reconstrucción de remate a puerta;
- penalti y su resultado;
- diferencias y solapamientos entre events, shot_events y shots;
- estrategia para evitar duplicar remates presentes en más de una fuente.

No se implementa `match_events` definitivo hasta cerrar este mapping.

## 10. Data Collector — variables aprobadas

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

Pendiente:

- definición operativa de falta peligrosa;
- confirmar `CORNER | FOR/AGAINST`;
- decidir resultado de ABP solo si es reproducible y útil;
- interfaz exacta de portero;
- mapping técnico de remates y penaltis desde DATA-03.

## 11. Mapping Opta conocido antes de DATA-03

Agregados:

```text
Pase: totalPass / accuratePass
Pase largo: totalLongBalls / accurateLongBalls
Centro: totalCross / accurateCross
Asistencia: goalAssist
Regate: totalContest / wonContest
Remate: totalScoringAtt / blockedScoringAtt / goals
Defensa: totalTackle / wonTackle / interception / blockedPass / totalClearance
Falta: fouls / wasFouled
Pérdida: turnover / dispossessed
Disciplina: yellowCard / redCard
Penalti: penaltyConceded / penaltyWon
Portero: saves / divingSave / goalsConceded
```

Event type IDs conocidos:

```text
1  Pass
3  Take on
4  Foul
7  Tackle
8  Interception
9  Turnover
10 Save
12 Clearance
13 Miss
14 Post
15 Attempt saved
16 Goal
17 Card
32 Blocked pass
67 Dispossessed
77 Key pass
```

Estos IDs orientan la inspección, pero no sustituyen la validación de outcomes/qualifiers reales.

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

No se detallan ramas todavía.

## 14. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados calculados; no inventa métricas ni sustituye cálculos críticos.

## 15. Tests y GitHub Actions

Tests existentes:

```text
tests/test_data_pipeline.py
tests/test_lineup_import.py
```

Durante desarrollo, el workflow `.github/workflows/tests.yml` queda **manual (`workflow_dispatch`)** para evitar emails repetitivos por cada commit/push. Antes de publicar el TFM se deben reactivar `push` y `pull_request` y dejar CI verde.

La validación con datos reales locales tiene prioridad sobre un test sintético.

## 16. Decisiones descartadas / no aprobadas

- No usar todas las variables Opta solo porque existan.
- No construir todavía el árbol experto detallado.
- No construir Feature Engine definitivo sobre DATA no estable.
- No publicar datasets completos de PannaData/Opta.
- No usar Getafe como demostrador principal.
- No duplicar pérdidas derivadas de pase/regate fallado.
- No crear botón separado para remate al poste.
- No convertir minutos nulos en 0 sin evidencia.
- No inferir formación a partir de `formation_place` sin una regla validada.
- No crear role stints si la fuente no permite reconstruir cambios de rol.
- No inventar mappings de outcomes/qualifiers.

## 17. Problemas abiertos

- DATA-03: mapear eventos y tiros atómicos.
- Resolver remate a puerta y penalti desde fuentes reales.
- Evitar duplicados entre `opta_events`, `opta_shot_events` y `opta_shots`.
- Cerrar falta peligrosa/córners/ABP/portero en Collector.
- Crear anonimización.
- Definir normalización GPS.
- Mejorar reejecución incremental sin depender de `--reset`.
- Construir Feature Engine cuando DATA esté estable.

## 18. Siguiente paso exacto

Ejecutar sobre las fuentes locales reales:

```bash
python data/inspect_demo_events.py
```

Con esa salida se cierra el mapping real de DATA-03 y se implementa el importador de `match_events`.
