# Data layer

Fecha de sincronización: 03/10/2026

La capa `data/` es la base estructurada del Football Performance System.

## Objetivo

Convertir diferentes fuentes de entrada en un esquema común y reproducible sin mezclar datos brutos con métricas derivadas.

Fuentes actuales/previstas:

```text
Data Collector first-party
PannaData / Opta (desarrollo y validación)
GPS normalizado opcional
```

Unidad analítica principal:

```text
player_match = jugador + partido
```

Tablas/capas principales del producto:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
gps_imports
gps_player_map
gps_observations
player_match_features
player_match_gps_summary
decision_results
player_match_rating
```

## Principios

- raw y derived permanecen separados;
- imports reproducibles e idempotentes;
- ausencia y ambigüedad se preservan;
- ningún mapping obligatorio se resuelve mediante suposición silenciosa;
- ninguna capa analítica depende de nombres reales;
- IDs/provenance se mantienen para auditoría;
- datos profesionales de desarrollo no se redistribuyen automáticamente.

## Taxonomía de eventos

La tabla central de acciones es `match_events`.

Contrato lógico:

```text
action_type
subtype
outcome
qualifiers
```

La taxonomía first-party oficial está versionada en:

```text
collector/event_catalog.json
catalog_version=0.3.0
```

El Collector V1.1 ya consume/preserva esta taxonomía.

## Caso demostrador local

El desarrollo y la validación se han realizado sobre una temporada profesional completa usada como demostrador técnico.

Cobertura validada:

```text
matches=38
played player-match appearances=590
squad players=36
```

Los datos originales permanecen locales y no se publican en el repositorio.

## Pipeline de importación

### DATA-01 — esquema / fixtures

```bash
python data/run_stage1.py
```

Responsabilidad:
- inicializar/actualizar DuckDB;
- auditar fuentes;
- localizar los partidos objetivo;
- cargar `teams`, `matches`, `team_match`;
- validar integridad y duplicados.

### DATA-02 — jugadores / player_match / roles

```bash
python data/run_stage2.py
```

Responsabilidad:
- cargar jugadores y participación;
- minutos;
- titularidad cuando existe;
- posición/rol observado;
- alineaciones/formación cuando la fuente lo permite;
- `player_role_stints`;
- mantener ambigüedad si la fuente solo informa `Substitute`.

### DATA-03 — eventos

Los eventos externos se normalizan al contrato del Collector:

```text
source event
→ match_events
→ action_type + subtype + outcome + qualifiers
```

Se preserva `source_event_id` para trazabilidad y deduplicación.

Incluye las familias necesarias del MVP: pase, progresión, 1v1, remate, defensa, faltas, tarjetas, penalti, portero y ABP/córner cuando la fuente permite reconstruirlos.

### DATA-04 — materialización / validación final

La base local actual alimenta Feature Engine, Analytics, Match Rating, sistema experto, GPS, dashboard, Assistant y Reports.

Validación global de DB actual:

```text
demo_team_exists=PASS
matches=38
distinct_matches=38
duplicate_source_match_ids=0
missing_opponents=0
missing_source_match_ids=0
player_match_rows_present=PASS
match_event_rows_present=PASS
player_match_fixture_coverage=38
invalid_minutes=0
orphan_match_events=0
duplicate_source_events=0
Validation status: PASS
```

## Política fail-fast de mappings

Los importadores pueden resolver variantes conocidas de nombres de columna, pero una columna obligatoria no resuelta provoca error y muestra las columnas reales.

```text
campo desconocido → STOP + diagnóstico
```

Nunca:

```text
campo desconocido → suposición silenciosa
```

## GPS

GPS entra por una capa canónica separada:

```text
archivo proveedor / demo sintética
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
```

GPS es opcional y no modifica los datos técnicos raw ni el Match Rating.

## Archivos locales excluidos de Git

Entre otros:

```text
data/football_performance.duckdb
data/source_schema_audit.json
data/validation_report.json
*.parquet
```

Puede indicarse otra ubicación mediante argumentos de los runners o `FPS_DB_PATH` en las capas que lo soportan.

## Publicación

La base real/de desarrollo no se considera redistribuible por defecto.

La anonimización elimina identidad, pero **no concede derechos de redistribución**.

El contrato de publicación local se valida con:

```powershell
python publication\validate_public_demo.py --source <db_origen> --output <db_demo>
```

Estado actual:

```text
PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS
REDISTRIBUTION STATUS: NOT CLEARED
```

El paquete público final deberá usar un dataset sintético reproducible o un dataset abierto con licencia compatible si la licencia de la fuente profesional no permite redistribución.
