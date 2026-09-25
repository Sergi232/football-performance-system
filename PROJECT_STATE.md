# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe consultarse al iniciar una nueva sesión y prevalece sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Track A — DATA en implementación activa. Track B — Data Collector en paralelo.**

La arquitectura general ya está aprobada y no debe reabrirse sin una razón técnica concreta.

Estado operativo actual:

```text
arquitectura                         HECHO
esquema DuckDB v0.1                  HECHO
auditoría automática fuentes         HECHO Y VALIDADO CON DATOS REALES
fixtures demo                         HECHO Y VALIDADO: 38/38
players + player_match               HECHO Y VALIDADO: 590 filas / 38 partidos
validación BD                         PASS
test sintético integración           HECHO
DATA-01                               CERRADO 25/09/2026
lineups / formación / roles          SIGUIENTE — DATA-02
events / shots                       DESPUÉS — DATA-03
```

La base está diseñada de forma orientada a eventos. Decisiones pendientes del Collector como `CORNER`, falta peligrosa o resultado de ABP no bloquean la infraestructura DATA.

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

La aplicación web es el producto principal del TFM.

## 3. Principios y decisiones aprobadas

- Team Mode es el modo principal.
- Player Mode será complementario.
- Rival Mode será una extensión futura.
- El sistema principal debe funcionar sin datos del rival.
- GPS complementario, no obligatorio.
- Separación estricta entre datos brutos, features, modelos y conclusiones.
- Ninguna conclusión importante dependerá exclusivamente de un LLM.
- Evitar data leakage.
- Toda regla, umbral o peso debe justificarse con datos, literatura, validación o experimentación.
- Priorizar MVP funcional antes de aumentar complejidad.
- GitHub es la fuente de verdad técnica.
- Documentación oficial del repositorio/TFM en castellano.
- Nombres técnicos de código pueden estar en inglés.
- El caso demostrador se reconstruye con datos reales y se anonimiza antes de publicarse.
- Los importadores deben ser reproducibles y fail-fast.
- Una columna desconocida no puede sustituirse por una suposición silenciosa.
- Las filas sin información suficiente no se completan con valores inventados.
- Una decisión pendiente de interfaz no bloquea infraestructura si el modelo de datos ya puede representarla de forma genérica.

## 4. Arquitectura materializada

Documento:

```text
docs/ARCHITECTURE.md
```

Módulos:

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

## 5. Base de datos — v0.1

Motor inicial: **DuckDB**.

Archivos principales:

```text
data/schema.sql
data/init_database.py
data/README.md
requirements.txt
```

Unidad analítica principal:

```text
player_match = jugador + partido
```

Tablas/capas:

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

La taxonomía se almacena como datos, no como columnas fijas.

Lógica derivada aprobada ya implementada:

```text
PASS | ... | FAIL  → possession loss / FAILED_PASS
DRIBBLE | FAIL     → possession loss / FAILED_DRIBBLE
LOSS               → OTHER_TURNOVER / subtipo
```

No debe existir doble conteo de pérdidas.

## 6. Track A — DATA

### 6.1 Fuentes reales auditadas

Ruta local de desarrollo:

```text
C:\Users\sergi\Desktop\analisi_futbol\input\pannadata\
```

Auditoría real ejecutada el 25/09/2026:

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

Archivo auditor:

```text
data/audit_pannadata_sources.py
```

Salida local generada y no versionada:

```text
data/source_schema_audit.json
```

### 6.2 Stage 1 — fixtures VALIDADO

Archivos:

```text
data/import_demo_fixtures.py
data/run_stage1.py
```

Mapping real resuelto:

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

Resultado real:

```text
Deportivo Alavés 2025/26
38 fixtures importados
38 partidos distintos
0 source_match_id duplicados
0 rivales ausentes
0 source_match_id ausentes
VALIDATION PASS
```

El primer prototipo mezclaba 424 partidos porque detectaba `season` y `competition` pero no los aplicaba correctamente al filtro. Se corrigió antes de validar el Stage 1.

### 6.3 Stage 2A — players + player_match VALIDADO

Archivos:

```text
data/import_demo_player_match.py
data/run_stage2.py
```

Mapping real resuelto:

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

Resultado real:

```text
filas fuente sin minutos descartadas: 245
player_match importados:             590
cobertura:                            38/38 partidos
jugadores distintos:                 28
minutos inválidos:                   0
VALIDATION PASS
```

Decisión aprobada sobre minutos nulos:

- `opta_player_stats` contiene filas con `minsPlayed = NULL/NaN`.
- No se convierten automáticamente en 0 minutos.
- No se inventa participación.
- Esas 245 filas quedan fuera de `player_match` en Stage 2A.
- `opta_lineups` se utilizará en DATA-02 para identificar correctamente suplentes no utilizados, titularidad y contexto de alineación.

`started` no existe/resuelve en `opta_player_stats`, por lo que debe proceder de `opta_lineups` y no inferirse artificialmente.

### 6.4 Ejecución limpia reproducible

Durante la validación real se detectó una limitación de DuckDB al reejecutar un `UPSERT` sobre filas padre ya referenciadas por claves foráneas. Para una reconstrucción limpia del dataset normalizado se añadió:

```bash
python data/run_stage2.py --reset
```

`--reset` elimina únicamente la DuckDB generada por el proyecto y la reconstruye desde los Parquet originales. No modifica los Parquet fuente.

Pendiente técnico no bloqueante: mejorar la reejecución incremental sin `--reset` para que no dependa de actualizaciones de filas padre referenciadas.

### 6.5 Validación

Archivo:

```text
data/validate_demo_database.py
```

Checks validados hasta Stage 2A:

- demo team existente;
- 38 `team_match`;
- 38 partidos distintos;
- sin `source_match_id` duplicados;
- equipo demo presente en home/away;
- rival no nulo;
- source match id no nulo;
- `player_match` presente;
- cobertura player_match 38/38;
- minutos válidos.

`match_events` continúa PENDING hasta DATA-03.

### 6.6 Tests

```text
tests/test_data_pipeline.py
.github/workflows/tests.yml
```

El test sintético utiliza 38 partidos, jugadores demo y rival de control. GitHub Actions está definido; su estado de ejecución debe revisarse cuando sea necesario, pero no sustituye la validación realizada sobre PannaData real.

## 7. Track B — Data Collector

Catálogo versionado:

```text
collector/event_catalog.json
```

### Aprobado

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
- `LOSS` solo se usa cuando la pérdida no está explicada por pase/regate fallado.
- Poste se agrupa en `OFF_TARGET` para el MVP.

### Parcial

```text
PENALTY → WON / CONCEDED → GOAL / MISSED
```

La lógica general está aprobada; falta validar el mapping técnico.

### Pendiente

- criterio operativo de falta peligrosa;
- confirmar `CORNER | FOR/AGAINST`;
- decidir resultado de ABP solo si es reproducible y útil;
- interfaz exacta de portero;
- mapping exacto de remate a portería/penaltis desde shot events.

Estas decisiones no bloquean Track A.

## 8. Caso demostrador aprobado

**Deportivo Alavés — LaLiga 2025/26.**

Opta team id:

```text
4dtdjgnpdq9uw4sdutti0vaar
```

Motivos:

- temporada completa;
- sin competición europea;
- perfil menos extremo que otras alternativas analizadas;
- equilibrio razonable entre pase, juego directo, centros, defensa y faltas.

Los valores profesionales sirven para validar el sistema, no para aprobar automáticamente métricas finales.

## 9. Mapping PannaData/Opta conocido

Variables agregadas relevantes:

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

Type IDs de eventos conocidos:

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

No construir el mapping final de outcomes/qualifiers hasta inspeccionar las columnas reales de `opta_events` y fuentes específicas de tiros.

## 10. Anonimización

Antes de publicar el dataset demostrador:

```text
Deportivo Alavés → TEAM_001
jugadores         → PLAYER_001, PLAYER_002, ...
oponentes         → OPP_001, OPP_002, ...
IDs originales    → IDs internos
```

Se conservarán estadísticas, minutos, roles y estructura temporal.

Script previsto:

```text
scripts/build_anonymized_demo.py
```

Nunca se publicarán datasets completos originales de PannaData/Opta.

## 11. Sistema experto previsto

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

## 12. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados ya calculados; no inventa métricas ni sustituye cálculos críticos.

## 13. GitHub Issues

```text
#1 DATA-01 — Validar Stage 1/2A con PannaData real          CERRADO 25/09/2026
#2 DATA-02 — Importar lineups, formación y roles            ACTIVO / SIGUIENTE
#3 DATA-03 — Mapear events y shot events                    PENDIENTE
#4 COLLECTOR-01 — Cerrar variables pendientes del MVP       EN PARALELO
```

## 14. Problemas abiertos

- Implementar DATA-02 con `opta_lineups` usando columnas reales, sin inferir roles no observados.
- Obtener titularidad fiable, dorsal y formación desde lineups cuando estén disponibles.
- Crear `player_role_stints` solo si la fuente permite reconstruir cambios de rol de forma fiable.
- Mapear eventos atómicos en DATA-03.
- Resolver shots/penaltis desde las fuentes específicas de tiro.
- Cerrar falta peligrosa/córners/ABP/portero en el Collector.
- Crear proceso de anonimización.
- Definir normalización GPS.
- Mejorar reejecución incremental de Stage 1/2 sin necesitar `--reset`.
- Construir Feature Engine cuando la capa DATA esté estable.

## 15. Decisiones descartadas o no aprobadas

- No usar todas las variables Opta solo porque existan.
- No construir todavía el árbol experto detallado.
- No construir Feature Engine definitivo sobre una capa DATA no estable.
- No usar datos ficticios como caso principal pudiendo reconstruir una temporada real.
- No publicar datasets completos de PannaData/Opta.
- No usar Getafe como demostrador principal.
- No duplicar pérdidas derivadas de pase/regate fallado.
- No crear botón separado para remate al poste.
- No inventar mappings de columnas u outcomes si la fuente real no los confirma.
- No convertir automáticamente minutos nulos en 0.

## 16. Siguiente paso exacto

**DATA-02 — `opta_lineups` → titularidad + formación + roles.**

Objetivos mínimos:

```text
player_match.started
player_match.shirt_number, si la fuente lo permite
player_match.primary_role, solo con mapping fiable
team_match.starting_formation, si la fuente lo permite
player_role_stints, solo si los cambios de rol son reconstruibles sin inferencia arbitraria
```

Criterios:

- usar los mismos 38 partidos ya validados;
- inspeccionar primero las 17 columnas reales de `opta_lineups`;
- no inventar roles;
- cobertura 38/38;
- mantener separación entre datos brutos y derivados;
- añadir validación y test antes de cerrar DATA-02.

Después:

```text
DATA-03: opta_events + shot events → match_events
anonimización
→ Feature Engine
→ sistema experto
→ dashboard
→ LLM
→ PDF
```
