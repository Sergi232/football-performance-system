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

El esquema inicial está definido en:

```text
data/schema.sql
```

Versión actual:

```text
0.1.0
```

La tabla central de acciones es `match_events`.

La taxonomía de acciones no está codificada como columnas fijas. Se representa mediante:

```text
action_type
subtype
outcome
qualifiers
```

Esto permite cerrar posteriormente córners, faltas peligrosas o ABP sin rediseñar la base completa.

## Unidad analítica

La unidad principal del proyecto es:

```text
jugador + partido
```

representada por `player_match`.

Los eventos atómicos se conservan porque permiten:

- reconstruir agregados;
- enlazar vídeo;
- auditar cálculos;
- crear nuevas features sin volver a etiquetar el partido.

## Inicialización local

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear la base DuckDB:

```bash
python data/init_database.py
```

O indicar otra ruta:

```bash
python data/init_database.py --db C:/ruta/football_performance.duckdb
```

Los ficheros `.duckdb` son artefactos locales y no deben publicarse en GitHub.

## Próximo desarrollo de esta capa

1. auditar automáticamente los esquemas de los Parquet PannaData/Opta;
2. crear el importador del caso Deportivo Alavés 2025/26;
3. mapear fixtures, lineups y player stats;
4. mapear eventos atómicos;
5. reconstruir remates a portería y penaltis desde shot events/qualifiers;
6. ejecutar controles de integridad;
7. anonimizar el dataset demostrador para el repositorio.
