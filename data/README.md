# Data layer

La capa `data/` es la fuente estructurada del Football Performance System.

## Objetivo

Convertir diferentes fuentes de entrada en un esquema común y reproducible sin mezclar datos brutos con métricas derivadas.

Fuentes previstas:

```text
Data Collector
PannaData / Opta (desarrollo y validación)
GPS normalizado
```

Salida común:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
gps_*
player_match_features
decision_results
```

## Esquema

El esquema inicial está definido en `data/schema.sql`.

Versión actual:

```text
0.1.0
```

La tabla central de acciones es `match_events` y la unidad analítica principal es `player_match` (jugador + partido).

La taxonomía de eventos se almacena mediante:

```text
action_type
subtype
outcome
qualifiers
```

No se codifica cada acción como una columna distinta. Esto permite cerrar posteriormente córners, faltas peligrosas o ABP sin rediseñar la base completa.

## Caso demostrador

```text
Deportivo Alavés — LaLiga 2025/26
Opta team id: 4dtdjgnpdq9uw4sdutti0vaar
```

Los datos originales son locales y no se publican en el repositorio.

## Pipeline acumulativo

### Stage 1 — esquema + auditoría + fixtures

Desde la raíz del repositorio:

```bash
python data/run_stage1.py
```

Ejecuta:

```text
init_database.py
→ audit_pannadata_sources.py
→ import_demo_fixtures.py
→ validate_demo_database.py
```

Contrato:

- inicializa/actualiza DuckDB;
- audita nombres y tipos reales de los Parquet;
- localiza los partidos del Alavés por ID Opta;
- limita el caso a 2025/26;
- aborta por defecto si no obtiene exactamente 38 partidos;
- carga `teams`, `matches` y `team_match` de forma idempotente;
- valida duplicados e integridad básica.

### Stage 2A — jugadores y participación

La orden acumulativa recomendada es:

```bash
python data/run_stage2.py
```

`run_stage2.py` vuelve a ejecutar Stage 1 de forma idempotente y después ejecuta:

```text
opta_player_stats.parquet
→ import_demo_player_match.py
→ players
→ player_match
→ validate_demo_database.py
```

Contrato de Stage 2A:

- utiliza únicamente los 38 `source_match_id` validados en Stage 1;
- filtra explícitamente por el `source_team_id` del Alavés;
- requiere identificadores de partido, equipo, jugador y minutos;
- aborta ante duplicados jugador-partido;
- rechaza minutos negativos o superiores a 130;
- carga nombre, posición, titularidad y dorsal cuando la fuente los contiene;
- no inventa titularidad/posición cuando no están disponibles;
- exige cobertura de `player_match` en los 38 partidos una vez existen filas.

## Política fail-fast de mappings

Los importadores intentan resolver variantes habituales de nombres de columna, pero una columna obligatoria no resuelta provoca un error que muestra las columnas reales de la fuente.

Esto es deliberado:

```text
campo desconocido → STOP + diagnóstico
```

Nunca:

```text
campo desconocido → suposición silenciosa
```

La auditoría completa queda en:

```text
data/source_schema_audit.json
```

## Archivos locales excluidos de Git

```text
data/football_performance.duckdb
data/source_schema_audit.json
data/validation_report.json
*.parquet
```

Se puede indicar otra ubicación:

```bash
python data/run_stage2.py --input-dir C:/ruta/pannadata --db C:/ruta/football_performance.duckdb
```

## Siguiente etapa — lineups y roles

Después de validar Stage 2A se incorporará `opta_lineups.parquet` para completar de forma verificable:

```text
titularidad
formación inicial
posición/rol
cambios de rol/posición si la fuente lo permite
```

Salida:

```text
player_match (enriquecido)
player_role_stints
team_match.starting_formation
```

## Eventos

Después se mapeará `opta_events` al catálogo versionado del Collector:

```text
PannaData/Opta event
→ match_events
→ action_type + subtype + outcome + qualifiers
```

Se preservará `source_event_id` para trazabilidad y deduplicación.

## Tiros y penaltis

`opta_shot_events` / `opta_shots` se usarán para resolver explícitamente:

- remates a portería;
- bloqueos;
- goles;
- penaltis y resultado;
- qualifiers necesarios.

No se inferirá un resultado crítico si la fuente no permite reconstruirlo de forma verificable.

## Principios de esta capa

- datos originales y derivados separados;
- imports reproducibles e idempotentes;
- ninguna dependencia de nombres reales en las capas analíticas;
- no publicar copias completas de PannaData/Opta;
- anonimizar el demostrador antes de incorporarlo al repositorio público;
- validar cada etapa antes de habilitar la siguiente.
