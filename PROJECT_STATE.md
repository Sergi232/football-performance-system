# PROJECT_STATE

Última actualización: 25/09/2026

Este archivo es la memoria técnica operativa del proyecto. Debe consultarse al iniciar una nueva sesión y prevalece sobre conversaciones antiguas cuando exista una contradicción.

## 1. Fase actual

**Track A — DATA en implementación activa. Track B — Data Collector en paralelo.**

La arquitectura general ya está aprobada y no debe reabrirse sin una razón técnica concreta.

Se ha abandonado el enfoque de esperar a cerrar el 100 % del Data Collector antes de programar. La base está diseñada de forma orientada a eventos, por lo que decisiones pendientes como `CORNER`, falta peligrosa o resultados de ABP no bloquean la infraestructura.

Estado operativo actual:

```text
arquitectura                  HECHO
esquema DuckDB v0.1           HECHO
auditoría automática fuentes  HECHO (código)
import fixtures demo          HECHO (código)
import player_match           HECHO (código)
validación BD                 HECHO (código)
test sintético integración    HECHO (código)
validación con PannaData real PENDIENTE DE EJECUCIÓN LOCAL
lineups / roles               SIGUIENTE DESPUÉS DE VALIDAR DATOS REALES
events / shots                DESPUÉS
```

El código no se considera validado contra PannaData real hasta ejecutarlo sobre los Parquet locales.

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
- Los importadores deben ser reproducibles, idempotentes y fail-fast.
- Una columna desconocida no puede sustituirse por una suposición silenciosa.

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

Regla de desbloqueo:

> Una decisión pendiente de interfaz no debe bloquear infraestructura si el modelo de datos ya puede representarla de forma genérica.

## 5. Base de datos — v0.1

Archivos:

```text
data/schema.sql
data/init_database.py
data/README.md
requirements.txt
```

Motor inicial: **DuckDB**.

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

## 6. Track A — pipeline DATA implementado

### 6.1 Auditoría de fuentes

Archivo:

```text
data/audit_pannadata_sources.py
```

Salida local:

```text
data/source_schema_audit.json
```

Audita:

- existencia;
- filas;
- columnas;
- nombres reales;
- tipos.

Fuentes objetivo:

```text
opta_fixtures.parquet
opta_lineups.parquet
opta_player_stats.parquet
opta_players.parquet
opta_events.parquet
opta_shot_events.parquet
opta_shots.parquet
opta_match_xg.parquet
```

### 6.2 Stage 1 — fixtures

Archivos:

```text
data/import_demo_fixtures.py
data/run_stage1.py
```

`import_demo_fixtures.py`:

- inspecciona el esquema real de `opta_fixtures.parquet`;
- resuelve variantes de nombres de columnas;
- aborta si faltan campos obligatorios;
- filtra por Opta team id del Alavés;
- limita a 2025/26 cuando existe fecha;
- exige 38 partidos por defecto;
- genera IDs internos deterministas;
- carga `teams`, `matches`, `team_match`;
- es idempotente.

Una orden ejecuta Stage 1:

```bash
python data/run_stage1.py
```

### 6.3 Stage 2A — players + player_match

Archivos:

```text
data/import_demo_player_match.py
data/run_stage2.py
```

`import_demo_player_match.py`:

- requiere Stage 1 válido;
- usa exclusivamente los 38 `source_match_id` ya aprobados;
- filtra explícitamente por source team id;
- exige `match_id`, `team_id`, `player_id` y minutos;
- detecta y bloquea duplicados jugador-partido;
- rechaza minutos <0 o >130;
- carga `players` y `player_match`;
- añade nombre, posición, titularidad y dorsal si existen;
- deja `NULL` cuando la fuente no permite conocer un dato, en lugar de inventarlo;
- es idempotente.

Orden acumulativa recomendada:

```bash
python data/run_stage2.py
```

Esta orden vuelve a ejecutar Stage 1 de forma segura y luego Stage 2A.

### 6.4 Validación

Archivo:

```text
data/validate_demo_database.py
```

Checks actuales:

- demo team existente;
- 38 `team_match`;
- 38 partidos distintos;
- sin `source_match_id` duplicados;
- equipo demo presente realmente en home/away;
- rival no nulo;
- source match id no nulo;
- presencia de `player_match` cuando Stage 2 está cargado;
- cobertura player_match 38/38;
- minutos válidos;
- controles básicos sobre `match_events` cuando existan.

Salida local:

```text
data/validation_report.json
```

### 6.5 Tests

Archivo:

```text
tests/test_data_pipeline.py
```

El test genera datos sintéticos con:

```text
38 partidos
2 jugadores demo por partido
1 jugador rival de control
```

y ejecuta dos veces los importadores para comprobar idempotencia.

Workflow creado:

```text
.github/workflows/tests.yml
```

El workflow instala Python 3.13 + dependencias y ejecuta `pytest -q`.

Estado a 25/09/2026: el workflow está definido, pero todavía no se ha observado una ejecución en GitHub Actions desde el conector.

## 7. Track B — Data Collector

Catálogo versionado:

```text
collector/event_catalog.json
```

### Aprobado

Pases:

```text
PASS | NORMAL | SUCCESS/FAIL
PASS | LONG   | SUCCESS/FAIL
PASS | CROSS  | SUCCESS/FAIL
```

`LONG` y `CROSS` cuentan automáticamente como pases totales.

Regate:

```text
DRIBBLE | SUCCESS/FAIL
```

Remate:

```text
SHOT | GOAL
SHOT | ON_TARGET
SHOT | OFF_TARGET
SHOT | BLOCKED
```

Poste se agrupa en `OFF_TARGET` para el MVP.

Defensa:

```text
TACKLE
INTERCEPTION
BLOCK
CLEARANCE
```

Falta y disciplina:

```text
FOUL | COMMITTED
FOUL | RECEIVED
CARD | YELLOW
CARD | RED
```

Pérdida:

```text
LOSS | OTHER
```

solo cuando no está explicada por pase/regate fallado.

### Parcial

Penalti:

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

## 8. Datos de desarrollo

Ruta de fuentes locales:

```text
C:\Users\sergi\Desktop\analisi_futbol\input\pannadata\
```

Base local preexistente:

```text
C:\Users\sergi\Desktop\analisi_futbol\outputs\base_pannadata.duckdb
```

Las tablas derivadas de proyectos anteriores no se utilizan automáticamente como fuente original del TFM.

Auditoría previa LaLiga 2025/26 confirmada:

```text
20 equipos
380 partidos
38 partidos por equipo
100 % fixtures
100 % player stats
100 % lineups
100 % events
```

## 9. Caso demostrador aprobado

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

## 10. Mapping PannaData/Opta conocido

Variables agregadas disponibles relevantes:

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

Todavía no se debe construir el mapping final de outcomes/qualifiers hasta inspeccionar las columnas reales de `opta_events` y las fuentes de tiros.

## 11. Anonimización

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

## 12. Sistema experto previsto

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

## 13. LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → LLM → COACH
```

El LLM explica resultados ya calculados; no inventa métricas ni sustituye cálculos críticos.

## 14. División de trabajo en GitHub Issues

Issues activos:

```text
#1 DATA-01 — Validar Stage 1/2A con PannaData real
#2 DATA-02 — Importar lineups, formación y roles
#3 DATA-03 — Mapear events y shot events al catálogo normalizado
#4 COLLECTOR-01 — Cerrar variables pendientes del MVP
```

DATA-01 es el cuello de botella operativo inmediato porque requiere acceso a los ficheros locales reales.

## 15. Problemas abiertos

- Validar los nombres reales de columnas contra los importadores automáticos.
- Comprobar Stage 1/2A sobre los Parquet reales.
- Completar lineups/formación/roles.
- Mapear eventos atómicos.
- Resolver shots/penaltis desde las fuentes específicas de tiro.
- Cerrar falta peligrosa/córners/ABP/portero en el Collector.
- Crear proceso de anonimización.
- Definir normalización GPS.
- Construir Feature Engine cuando la capa DATA esté estable.

## 16. Decisiones descartadas o no aprobadas

- No usar todas las variables Opta solo porque existan.
- No construir todavía el árbol experto detallado.
- No construir Feature Engine definitivo sobre una capa DATA no validada.
- No usar datos ficticios como caso principal pudiendo reconstruir una temporada real.
- No publicar datasets completos de PannaData/Opta.
- No usar Getafe como demostrador principal.
- No duplicar pérdidas derivadas de pase/regate fallado.
- No crear botón separado para remate al poste.
- No inventar mappings de columnas u outcomes si la fuente real no los confirma.

## 17. Siguiente paso exacto

### Acción local inmediata

Desde la raíz del repositorio:

```bash
python data/run_stage2.py
```

Resultado esperado:

```text
Stage 1:
  DuckDB inicializado
  auditoría de fuentes generada
  38 fixtures importados
  validación PASS

Stage 2A:
  players/player_match importados
  cobertura 38/38
  validación PASS
```

Si un mapping falla, el propi script mostrará las columnas reales que no ha podido resolver. Esa salida se utiliza para corregir el mapping de forma explícita.

### Inmediatamente después de DATA-01

```text
DATA-02: opta_lineups → titularidad + formación + roles
DATA-03: opta_events + shot events → match_events
anonimización
→ Feature Engine
→ sistema experto
→ dashboard
→ LLM
→ PDF
```
