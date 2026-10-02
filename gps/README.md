# GPS — contrato normalizado multi-proveedor

Fecha de sincronización: 03/10/2026

## Objetivo

GPS es una fuente **opcional y complementaria**. El sistema debe seguir funcionando sin GPS.

La capa GPS normaliza archivos de distintos proveedores a un esquema común sin hacer depender Features, Analytics, dashboard o Reports de nombres de columnas, unidades o formatos propietarios.

```text
archivo proveedor / demo sintética
→ mapping declarativo
→ normalización de unidades/campos
→ control de calidad
→ mapping explícito de jugador
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / reports
```

## Principio metodológico

La capa GPS conserva datos raw/normalizados y provenance.

No fija métricas canónicas de:
- HSR;
- sprint;
- workload;
- fatiga;
- readiness/disponibilidad física;
- riesgo de lesión.

Si un proveedor entrega métricas ya calculadas, pueden conservarse como dato de proveedor con su definición/threshold, pero no se convierten automáticamente en definición canónica del sistema.

## Esquema canónico por muestra

| Campo | Unidad canónica | Regla |
|---|---:|---|
| `source_player_key` | texto | Identificador del jugador dentro del proveedor. No sustituye a `player_id`. |
| `timestamp_ms` | ms | Tiempo normalizado; `gps_imports.time_basis` documenta el cero. |
| `x` | m | Opcional. Solo si la fuente puede expresarse de forma segura en metros. |
| `y` | m | Opcional. Solo si la fuente puede expresarse de forma segura en metros. |
| `distance_m` | m | Distancia incremental de la muestra. |
| `speed_m_s` | m/s | Velocidad instantánea si existe. |
| `acceleration_m_s2` | m/s² | Aceleración/desaceleración instantánea. |
| `source_row_number` | entero | Trazabilidad con la fila original. |
| `quality_flags` | texto/JSON | Incidencias detectadas sin inventar valores. |

No se fuerzan coordenadas tácticas si la fuente no permite una transformación segura.

## Metadatos de importación

`gps_imports` conserva:
- proveedor/archivo;
- `source_format`;
- `sample_rate_hz`;
- `time_basis`;
- `coordinate_system`;
- `distance_mode`;
- `source_units`;
- `mapping_config`;
- notas de importación.

## Mapping de jugador

`gps_player_map` conserva:

```text
gps_import_id
source_player_key
source_player_name
player_id
mapping_method
mapping_confidence
```

No existe fuzzy matching silencioso. Un identificador de proveedor entra en `gps_observations` solo cuando está vinculado explícitamente a un `player_id`.

## Mapping declarativo y normalizador

Ejemplo:

```text
gps/mapping_schema.example.json
```

Normalizador genérico:

```text
gps/normalize_csv.py
```

El mapping declara columnas, unidades, formato de distancia, delimitador/codificación y metadatos del proveedor.

## Conversiones soportadas

- tiempo: segundos ↔ milisegundos según mapping;
- distancia: km → m; m → m;
- velocidad: km/h → m/s; m/s → m/s;
- aceleración: g → m/s²; m/s² → m/s²;
- distancia acumulada → incremental por jugador.

No se convierten coordenadas geográficas a metros sin transformación explícita.

## Calidad

El normalizador no rellena valores ausentes. Puede marcar:
- `NON_MONOTONIC_TIMESTAMP`;
- `CUMULATIVE_DISTANCE_RESET`;
- `NEGATIVE_DISTANCE`;
- `NEGATIVE_SPEED`;
- `INVALID_<FIELD>`.

Los valores imposibles quedan vacíos y el flag preserva la incidencia.

## Resumen físico descriptivo

Builder:

```text
analytics/build_gps_physical_summary.py
```

Versión vigente:

```text
gps_physical_summary_v0.1-descriptive
```

Salida:

```text
player_match_gps_summary
```

El summary es descriptivo. No deriva claims de fatiga, calidad, lesión o readiness.

## Precedencia de fuentes

Regla cerrada:

```text
GPS REAL / observado
→ prioridad sobre GPS sintético para el mismo jugador-partido
→ imported_at solo desempata dentro de la misma clase de fuente
```

El validator contiene un fixture real-antiguo vs synthetic-reciente y exige seleccionar el real.

Estado:

```text
source_precedence_fixture=REAL_OVER_SYNTHETIC:PASS
```

## Demo sintética integrada

Generador:

```text
gps/generate_synthetic_demo.py
generator_version=gps_synthetic_demo_v1.2.0
```

Provenance obligatoria:

```text
provider=FPS Synthetic Demo
source=SYNTHETIC_DEMO_NOT_OBSERVED
mapping_config.synthetic_demo=true
```

Cobertura local validada:

```text
appearances=590
imports=38
player_maps=590
observations=38197
summary_rows=590
latest_rows=590
```

La demo entra por las mismas tablas canónicas que un proveedor real:

```text
jugador-partido + minutos + rol cuando existe
→ generador determinista
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ app/gps_physical_access.py
→ dashboard Físico / GPS
→ Reports V6 Team / Player / Match
```

El generador está condicionado por minutos y grupo de posición cuando la fuente lo permite, pero sus priors no son umbrales científicos ni referencias normativas.

Cobertura de rol contextual en la demo:
- 482/590 apariciones con rol resoluble;
- 108/590 permanecen `OTHER` porque la fuente no permite recuperar una posición fiable.

No se inventa posición para esas apariciones.

La correlación minutos-distancia validada en la demo es una propiedad de generación interna, no evidencia fisiológica real.

## Separación respecto a Analytics/Expert

GPS sintético:
- no modifica Match Rating;
- no modifica Performance Index;
- no alimenta decisiones expertas como evidencia física observada;
- no crea fatiga/readiness/risk claims.

N9000 cuenta solo GPS **observado no sintético** como disponibilidad física experta.

En la DB local actual:

```text
player-match rows with observed non-synthetic GPS: 0
```

Esto es correcto: la capa física demo puede estar operativa mientras el Expert System sigue declarando ausencia de GPS observado.

## Validaciones

### Normalización GPS

```powershell
python gps\run_stage1.py
```

### Demo sintética

```powershell
python gps\validate_synthetic_demo.py --db <ruta_duckdb>
```

### Coherencia interna demo

```powershell
python gps\audit_synthetic_plausibility.py --db <ruta_duckdb>
```

### Summary / precedencia

```powershell
python gps\validate_physical_summary.py --db <ruta_duckdb>
```

Estado vigente:

```text
GPS SYNTHETIC DEMO CONTRACT: PASS
GPS SYNTHETIC COHERENCE AUDIT: PASS
GPS PHYSICAL SUMMARY CONTRACT: PASS
```

## Integración de producto

GPS descriptivo está integrado en:
- dashboard Físico / GPS;
- Team Mode;
- Player Mode;
- Match Mode;
- PDF Team / Player / Match V6.

La UI etiqueta explícitamente datos sintéticos como `DATOS DEMO · GPS sintético` cuando corresponde.
