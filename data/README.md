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

## Stage 1 — infraestructura + fixtures del demostrador

Caso demostrador local:

```text
Deportivo Alavés — LaLiga 2025/26
Opta team id: 4dtdjgnpdq9uw4sdutti0vaar
```

Una sola orden ejecuta el Stage 1 completo desde la raíz del repositorio:

```bash
python data/run_stage1.py
```

El pipeline hace, por orden:

```text
1. init_database.py
2. audit_pannadata_sources.py
3. import_demo_fixtures.py
4. validate_demo_database.py
```

Contrato del Stage 1:

- inicializar/actualizar el esquema DuckDB;
- auditar nombres y tipos reales de las fuentes Parquet;
- localizar los partidos del equipo por su ID Opta;
- limitar el caso a la temporada 2025/26;
- abortar por defecto si no se obtienen exactamente 38 partidos;
- cargar `teams`, `matches` y `team_match` de forma idempotente;
- validar duplicados, identificadores, presencia del rival e integridad básica.

El importador es **fail-fast**: intenta resolver nombres de columnas comunes, pero si una columna obligatoria no existe muestra las columnas reales y se detiene. No sustituye un mapping desconocido por una suposición silenciosa.

Archivos locales generados y excluidos de Git:

```text
data/football_performance.duckdb
data/source_schema_audit.json
data/validation_report.json
```

Se puede indicar otra ubicación:

```bash
python data/run_stage1.py --input-dir C:/ruta/pannadata --db C:/ruta/football_performance.duckdb
```

## Stage 2 — participación y jugadores

Una vez validado Stage 1:

```text
opta_players + opta_lineups + opta_player_stats
        ↓
players
player_match
player_role_stints
```

Controles mínimos previstos:

- cobertura de los 38 partidos;
- minutos válidos;
- titular/suplente;
- posición/rol disponible;
- ausencia de duplicados jugador-partido.

## Stage 3 — eventos

Después se mapeará `opta_events` al catálogo versionado del Collector:

```text
PannaData/Opta event
        ↓
match_events
        ↓
action_type + subtype + outcome + qualifiers
```

Se preservará el `source_event_id` para trazabilidad y deduplicación.

## Stage 4 — tiros y penaltis

`opta_shot_events` / `opta_shots` se usarán para resolver de forma explícita:

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
