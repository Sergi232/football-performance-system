# Publicación y reproducibilidad

Fecha de sincronización: 03/10/2026

Este bloque separa dos objetivos distintos:

1. **anonimizar localmente** el caso profesional usado durante desarrollo;
2. disponer de una **demo pública 100% sintética y reproducible** que no copie filas de la fuente profesional.

## 1. Regla de licencia

La anonimización técnica **no equivale a permiso de redistribución**.

Por tanto:

```text
professional source data
→ anonymized local export
→ útil para QA local
→ REDISTRIBUTION NOT CLEARED
```

Si la licencia de la fuente no autoriza redistribución, esa exportación no se publica aunque nombres e IDs estén anonimizados.

## 2. Demo anonimizada local

Scripts existentes:

```text
publication/build_public_demo.py
publication/validate_public_demo.py
```

La exportación local conserva un subconjunto de tablas del caso real con IDs/nombres neutralizados y valida:
- ausencia de identificadores originales;
- identidad de row counts en las tablas exportadas;
- gate seguro N13000;
- metadata de anonimización.

Estado actual:

```text
PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS
REDISTRIBUTION STATUS: NOT CLEARED
```

Esta vía **no es el paquete público final** mientras no exista autorización de licencia.

## 3. Demo pública sintética reproducible

Builder:

```text
publication/build_synthetic_demo.py
```

Validator end-to-end:

```text
publication/validate_synthetic_demo.py
```

La base se genera desde cero con seed determinista y metadata explícita:

```text
demo_version=synthetic_public_demo_v0.1.0
data_origin=SYNTHETIC_GENERATED_FROM_SCRATCH
contains_professional_source_rows=False
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

No copia filas, nombres, IDs, source IDs ni provenance de PannaData/Opta.

### Qué se calcula con código real del proyecto

A partir de estadísticas raw sintéticas:
- FEATURE-01;
- FEATURE-02 strict-past;
- FEATURE-03 role-conditioned;
- ANALYTICS-01;
- EXPERT-01..07 / N1000-N13000;
- GPS physical summary;
- Attention Centre.

El builder reutiliza los módulos del proyecto; no duplica su lógica.

### Qué se materializa como fixture de compatibilidad

`Match Rating V5` y `Performance Index` usan filas sintéticas compatibles con el contrato de producto, marcadas explícitamente como fixtures.

Motivo: el Match Rating V5 validado depende de artefactos/calibraciones de investigación que no forman parte del dataset público redistribuible.

Por tanto, la demo pública demuestra:
- integración;
- UI;
- schemas/contratos;
- navegación;
- Assistant sobre outputs estructurados;
- Reports;
- pipeline determinista que sí es reproducible sobre datos sintéticos.

Pero **no** se presenta como revalidación científica del Match Rating V5 ni del Performance Index.

## 4. Construir + validar desde un clone limpio

Desde la raíz del repositorio:

```powershell
python publication\validate_synthetic_demo.py --rebuild
```

El comando crea por defecto:

```text
data/football_performance_synthetic_demo.duckdb
```

La DuckDB se ignora por Git; cualquiera puede regenerarla a partir del código.

Gate esperado:

```text
SYNTHETIC PUBLIC DEMO CONTRACT: PASS
professional_source_rows=0
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
app_read_layer=PASS
report_payloads=PASS
```

## 5. Ejecutar la web con la demo sintética

```powershell
$env:FPS_DB_PATH="$PWD\data\football_performance_synthetic_demo.duckdb"
$env:FPS_DEMO_MODE="1"
streamlit run app\streamlit_app.py
```

No se necesita la DuckDB profesional para esta demo.

## 6. Dos gates distintos

```text
ANONYMIZED LOCAL DEMO
= protege identidad
= NO resuelve licencia

SYNTHETIC PUBLIC DEMO
= generado desde cero
= reproducible
= redistribuible como demo sintética
```

Nunca mezclar ambos claims en README, memoria o defensa.
