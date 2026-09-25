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
FEATURE-01 base determinista             SIGUIENTE
Sistema experto                          DESPUÉS DE FEATURES
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
collector/       captura de vídeo/manual y taxonomía
data/            esquema, imports y datos normalizados
gps/             contrato y normalización multi-proveedor
features/        variables derivadas
engine/          análisis determinista
decision_tree/   sistema experto auditable
models/          ML opcional
app/             dashboard web
llm/             consulta y explicación
reports/         exportación PDF
tests/           regresión y validación
```

Base: DuckDB. Unidad analítica principal: `player_match = jugador + partido`.

## 5. Base de datos

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

### Regla de procedencia

No se fuerza a que todas las métricas procedan de eventos atómicos. Cada métrica debe usar la fuente canónica más fiable y conservar su procedencia.

## 6. Caso demostrador

```text
Deportivo Alavés — LaLiga 2025/26
Opta team id: 4dtdjgnpdq9uw4sdutti0vaar
38 partidos
36 jugadores tras lineups
```

Antes de publicar se anonimizará:

```text
TEAM_001
PLAYER_001...
OPP_001...
IDs internos
```

Nunca se publicarán datasets completos originales de PannaData/Opta.

## 7. DATA — estado cerrado

### DATA-01

- 38 fixtures.
- 590 player_match iniciales con participación.
- 0 duplicados de partido.
- validación PASS.

### DATA-02

- 835 filas finales de `player_match`.
- 418 titulares = 38 x 11.
- 245 suplentes con 0 minutos incorporados desde lineups.
- 36 jugadores distintos.
- no se infiere formación desde `formation_place`.
- no se crean role stints que la fuente no permite reconstruir.

### DATA-03

`opta_events.parquet` no es un feed atómico completo en este export. No se inventan pases, regates, tackles, intercepciones, faltas o pérdidas.

Remates:

```text
shot_events fuente                    464
autogol excluido                        1
SHOT importados                        463
cobertura                            38/38
```

Validación de contrato:

```text
total_shots mismatches                  0
shots_off_target mismatches             0
goals mismatches                        0
shots_penalty mismatches                0
shots_on_target bound mismatches        0
on_target + blocked mismatches          0
shots_blocked          AGGREGATE_CANONICAL
```

Tarjetas: 98 importadas; 2 son eventos de equipo sin atribución de jugador y se guardan con `player_id=NULL`.

### DATA-04

`player_match_raw_stats`: 835/835 filas, 38/38 partidos, 36 jugadores. Validación PASS.

27 estadísticas raw:

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

`key_passes` es una variable útil del sistema/Collector, pero este export no contiene una columna verificada equivalente. No se aproxima con otra estadística.

Los `NULL` de la fuente se preservan como `NULL`.

## 8. COLLECTOR-01 — CERRADO FUNCIONALMENTE

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

Qualifiers controlados:

```text
key_pass
assist
second_yellow
set_piece_result
penalty_taker_player_id
```

Decisiones:

- LONG/CROSS cuentan también como pase total.
- PASS FAIL y DRIBBLE FAIL generan pérdida derivada.
- LOSS se reserva a otras pérdidas.
- poste agrupado en OFF_TARGET en MVP.
- tackles total/ganado quedan diferenciados.
- falta peligrosa no es un botón subjetivo: se captura x/y y se derivará cuando exista criterio validado.
- córners/faltes conservan tiempo de partido/vídeo para clips ABP.

Versión funcional: `collector/data_collector_futbol_mvp.html`.

Validación local:

```text
COLLECTOR MVP VALIDATION: PASS
catalog actions covered: 20/20
CSV eventos + CSV resumen + JSON: OK
foul x/y + ABP: OK
role/side + formation changes: OK
```

Aceptado funcionalmente el 25/09/2026. Retocs visuals/UX: backlog no bloqueante.

## 9. GPS-01 — CERRADO / VALIDADO

GPS es opcional. Contrato normalizado multi-proveedor implementado en `gps/`.

Unitats canòniques:

```text
timestamp_ms      milisegundos
distance_m        metros
speed_m_s         m/s
acceleration_m_s2 m/s²
x/y               metros cuando el mapping espacial es seguro
```

Implementado:

- `gps/mapping_schema.example.json`: mapping declarativo por proveedor.
- `gps/normalize_csv.py`: normalizador CSV genérico.
- distancia acumulada puede convertirse a incremento por muestra.
- `gps_player_map`: mapping explícito de identidad del proveedor a `player_id`.
- metadatos de proveedor, mapping y unidades en `gps_imports`.
- flags de calidad para timestamps, resets y valores físicamente imposibles.
- no hay fuzzy matching silencioso de jugadores.
- métricas propietarias del proveedor no se convierten automáticamente en features canónicas.

Validación local 25/09/2026:

```text
GPS-01 VALIDATION: PASS
schema_version: 0.4.0
mapping_version: 0.1.0
synthetic rows: 6
synthetic players: 2
quality-control flagged rows: 1
unit conversions: PASS
cumulative -> delta distance: PASS
gps_player_map + import metadata: PASS
```

No se han inventado umbrales de sprint, HIE o carga.

Cuando exista un fichero GPS real, solo habrá que crear/adaptar el mapping del proveedor y volver a validar.

## 10. Sistema experto previsto

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

Cada nodo debe mantener:

```text
entrada → condición → resultado → confianza → justificación
```

No se fijan ramas/umbrales finales antes de validar las features disponibles.

## 11. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica y consulta resultados estructurados. No inventa métricas ni sustituye cálculos críticos.

## 12. Decisiones descartadas / restricciones

- No usar todas las variables Opta solo porque existan.
- No duplicar pérdidas derivadas.
- No inferir formación sin evidencia.
- No crear role stints ficticios.
- No forzar semántica event-level desde agregados ambiguos de Opta.
- No tratar `opta_events` como feed atómico completo.
- No hacer que una estadística raw positiva cambie automáticamente los minutos de participación.
- No inventar umbrales GPS de sprint/HIE/carga antes de justificarlos.
- No usar fuzzy matching silencioso para identidades GPS.
- No convertir automáticamente métricas propietarias GPS en variables analíticas canónicas.

## 13. Problemas abiertos

- construir Feature Engine determinista v0.1;
- decidir posteriormente reglas de elegibilidad/muestra mínima para interpretación, sin alterar raw;
- añadir features físicas solo cuando haya datos GPS reales o una definición suficientemente justificada;
- crear script de anonimización para publicación;
- mejorar reejecución incremental de algunos imports;
- retocar UX del Collector al final de la fase funcional;
- determinar fuente de `key_passes` si aparece otro export fiable.

## 14. Siguiente paso exacto

Construir **FEATURE-01** sobre `player_match_raw_stats` + `player_match`:

1. catálogo explícito de features y procedencia;
2. ratios de efectividad puramente deterministas;
3. normalizaciones por 90 minutos solo cuando `minutes_played > 0`;
4. preservar `NULL` si falta el raw necesario;
5. no aplicar todavía ratings, pesos, percentiles, etiquetas de rendimiento o umbrales expertos;
6. escribir resultados versionados en `player_match_features`;
7. validar idempotencia, dominios y cobertura sobre los 38 partidos.

Después de FEATURE-01: incorporar tendencia/ventanas temporales leakage-safe y preparar las primeras ramas N1000/N2000/N3000 del sistema experto.
