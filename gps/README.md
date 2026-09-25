# GPS — contrato normalizado multi-proveedor

## Objetivo

GPS es una fuente **opcional y complementaria**. El sistema debe seguir funcionando sin GPS.

GPS-01 define una capa común para importar archivos de distintos proveedores sin hacer depender el Feature Engine de nombres de columnas, unidades o formatos propietarios.

```text
archivo proveedor
→ mapping declarativo
→ normalización de unidades/campos
→ control de calidad
→ mapping explícito de jugador
→ gps_observations
→ Feature Engine
```

## Principio metodológico

La capa GPS guarda datos raw/normalizados y su procedencia. No fija todavía métricas analíticas, zonas de velocidad, umbrales de sprint, carga o fatiga.

Si un proveedor entrega métricas ya calculadas (por ejemplo, high-speed running o número de sprints), podrán conservarse más adelante como dato raw con su definición/umbral de proveedor, pero **no se convertirán automáticamente en la definición canónica del sistema**.

## Esquema canónico por muestra

| Campo | Unidad canónica | Regla |
|---|---:|---|
| `source_player_key` | texto | Identificador del jugador dentro del proveedor. No sustituye a `player_id`. |
| `timestamp_ms` | ms | Tiempo normalizado. La base registra en `gps_imports.time_basis` qué representa el cero. |
| `x` | m | Opcional. Solo se importa si la fuente puede expresarse en metros. |
| `y` | m | Opcional. Solo se importa si la fuente puede expresarse en metros. |
| `distance_m` | m | Distancia **incremental de la muestra**, no acumulada. |
| `speed_m_s` | m/s | Velocidad instantánea si está disponible. |
| `acceleration_m_s2` | m/s² | Aceleración instantánea; valores negativos representan desaceleración. |
| `source_row_number` | entero | Trazabilidad con la fila original. |
| `quality_flags` | texto/JSON | Incidencias detectadas sin inventar valores. |

La posición `x/y` no se fuerza si el proveedor solo da latitud/longitud o un sistema de coordenadas no transformable de forma segura. La orientación del campo y la transformación a un marco táctico común se harán después si disponemos de la información necesaria.

## Metadatos de importación

`gps_imports` conserva, además del proveedor y archivo:

- `source_format`;
- `sample_rate_hz` si se conoce;
- `time_basis`;
- `coordinate_system`;
- `distance_mode` (`delta` o `cumulative` en origen);
- `source_units`;
- `mapping_config`;
- notas de importación.

## Mapping de jugador

Se crea `gps_player_map`:

```text
gps_import_id
source_player_key
source_player_name
player_id
mapping_method
mapping_confidence
```

No se hará fuzzy matching silencioso. Un identificador de proveedor solo entra a `gps_observations` cuando está vinculado de forma explícita a un `player_id` del sistema.

## Mapping declarativo

Cada proveedor se adapta mediante JSON. Ejemplo: `gps/mapping_schema.example.json`.

El mapping define:

- delimitador y codificación;
- nombres de columnas origen;
- unidades origen;
- si la distancia es incremental o acumulada;
- metadatos del proveedor.

El normalizador genérico es `gps/normalize_csv.py`.

## Conversiones soportadas en GPS-01

- tiempo: segundos → milisegundos; milisegundos → milisegundos;
- distancia: km → m; m → m;
- velocidad: km/h → m/s; m/s → m/s;
- aceleración: g → m/s²; m/s² → m/s²;
- distancia acumulada → distancia incremental por jugador.

No se convierten coordenadas geográficas a metros sin una transformación explícita.

## Calidad

El normalizador no rellena valores ausentes. Marca, entre otros:

- `NON_MONOTONIC_TIMESTAMP`;
- `CUMULATIVE_DISTANCE_RESET`;
- `NEGATIVE_DISTANCE`;
- `NEGATIVE_SPEED`;
- `INVALID_<FIELD>`.

Los valores imposibles se dejan vacíos en la salida normalizada y se conserva el flag.

## Validación

Como todavía no hay un archivo GPS real aprobado en el proyecto, GPS-01 se valida primero con un fixture sintético que simula un proveedor distinto:

```bash
python gps/run_stage1.py
```

Este runner:

1. aplica la migración GPS a DuckDB;
2. ejecuta el normalizador con unidades diferentes;
3. comprueba conversiones, esquema, mapping de jugador y controles de calidad.

Cuando se disponga de un archivo real de un proveedor, se añadirá su mapping sin cambiar el contrato canónico salvo evidencia clara.
