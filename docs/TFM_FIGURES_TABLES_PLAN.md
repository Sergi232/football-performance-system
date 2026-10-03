# TFM — Plan de figuras, tablas y anexos

Fecha: 03/10/2026
Estado: plan de producción académica.

Objetivo: definir qué elementos visuales y tablas necesita la memoria final, qué evidencia debe alimentar cada uno y qué afirmaciones pueden sostener. Ninguna figura debe contener cifras reconstruidas manualmente si existe una fuente reproducible en el repositorio.

---

# 1. Figuras principales

## Figura 1 — Arquitectura general del sistema

Contenido:

```text
VIDEO / COLLECTOR + GPS OPCIONAL
→ RAW / NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / DS-ML
→ PRODUCT SERVICE / ACCESS
→ DASHBOARD
   ↓              ↓
ASSISTANT IA      PDF
```

Fuente:
- `docs/ARCHITECTURE.md`;
- `PROJECT_STATE.md`.

Claim permitido:
- el producto está diseñado por capas y separa cálculo, decisión y lenguaje.

No usar para afirmar:
- que cada capa mejora causalmente el rendimiento deportivo.

---

## Figura 2 — Separación DATA → ANALYTICS → DECISION ENGINE → LLM

Contenido:

```text
DuckDB
→ features / analytics materializados
→ expert system
→ read-only tools
→ router
→ Ollama local
→ semantic guard
→ Coach Copilot
```

Fuente:
- `llm/`;
- `docs/ARCHITECTURE.md`;
- `PROJECT_STATE.md`.

Claim permitido:
- el LLM se encuentra downstream de la lógica crítica y no es el motor de cálculo.

---

## Figura 3 — Flujo del Data Collector

Contenido visual recomendado:
- captura desktop real del Collector V1.1;
- pequeña leyenda de familias de acciones;
- flujo `evento observable → raw event → raw stats → feature`.

Fuente:
- `collector/data_collector_futbol.html`;
- `collector/event_catalog.json`;
- `collector/COLLECTOR_MVP.md`.

Claim permitido:
- el collector registra hechos observables definidos por taxonomía.

Precaución:
- no afirmar validación visual móvil real en múltiples dispositivos; el gate mobile/responsive es contractual/estructural.

---

## Figura 4 — Modelo de datos simplificado

Entidades a mostrar:

```text
teams
players
matches
team_match
player_match
player_role_stints
match_events
player_match_raw_stats
player_match_features
analytics_evidence
decision_results
gps_imports
gps_player_map
gps_observations
player_match_gps_summary
```

Fuente:
- `data/schema.sql`;
- `data/migrations/`.

Objetivo:
- explicar la separación entre raw, derived y decision data.

---

## Figura 5 — Control temporal strict-past

Diagrama conceptual:

```text
M1 ── M2 ── M3 ── M4
          ↑
      fila actual

permitido: M1, M2
prohibido: M3 actual, misma fecha, M4 futuro
```

Fuente:
- `features/build_temporal_features.py`;
- `features/build_role_temporal_features.py`;
- `analytics/build_stage1.py`.

Claim permitido:
- las features temporales no utilizan información futura según contrato y validación del proyecto.

---

## Figura 6 — Sistema experto N1000-N13000

Representación recomendada:

```text
N1000 actividad
N2000 perfil
N3000 forma
N4000 amenaza ofensiva
N5000 creación
N6000 defensa
N7000 finalización
N8000 contexto equipo
N9000 físico
N10000 rol/contexto
N11000 consistencia
N12000 fit evidence
N13000 recommendation gate
```

Añadir lateralmente:

```text
input → condition → result → confidence → justification
```

Fuente:
- `decision_tree/`;
- `decision_tree/catalog.json`;
- `PROJECT_STATE.md`.

Claim permitido:
- arquitectura modular y auditable.

No presentar N13000 como recomendador táctico validado: actualmente es un gate seguro.

---

## Figura 7 — Match Rating frente a Performance Index

Diseño conceptual:

```text
MATCH RATING V5
partido actual
jugador-partido
inmediato

PERFORMANCE INDEX
histórico
posicional
experimental
```

Fuente:
- `docs/MATCH_RATING_PRODUCT_CONTRACT.md`;
- `PROJECT_STATE.md`.

Objetivo:
- evitar que el lector confunda ambas capas.

---

## Figura 8 — GPS normalizado y precedencia de fuente

Contenido:

```text
provider A / provider B / synthetic
→ normalization
→ gps_imports
→ gps_player_map
→ gps_observations
→ physical summary

REAL OBSERVED > SYNTHETIC
```

Fuente:
- `gps/README.md`;
- `analytics/build_gps_physical_summary.py`.

Claim permitido:
- existe una capa común multi-proveedor y una precedencia explícita.

No representar synthetic GPS como evidencia fisiológica.

---

## Figura 9 — Capturas del dashboard

Capturas mínimas:
1. Team Mode;
2. Player Mode;
3. Match Mode;
4. Físico/GPS;
5. Coach Copilot.

Fuente:
- ejecución real de `app/streamlit_app.py` con `FPS_DEMO_MODE=1`.

Requisitos:
- nombres demo visibles;
- castellano;
- no exponer datos profesionales identificables;
- usar la misma resolución/aspecto cuando sea posible.

---

## Figura 10 — Reproducibilidad y CI

Contenido:

```text
clean clone
→ install requirements
→ pytest
→ build synthetic DB from scratch
→ validate app read layer
→ validate reports
→ PASS
```

Fuente:
- `.github/workflows/tests.yml`;
- `publication/build_synthetic_demo.py`;
- `publication/validate_synthetic_demo.py`.

Claim permitido:
- el producto puede validarse en un entorno limpio sin la DuckDB profesional.

---

# 2. Tablas principales

## Tabla 1 — Variables del Collector V1.1

Columnas:
- familia;
- variable/evento;
- raw o contexto;
- derivable sí/no;
- justificación de inclusión.

Fuente:
- `collector/event_catalog.json`;
- `collector/COLLECTOR_MVP.md`.

---

## Tabla 2 — Capas y versiones activas

Filas mínimas:
- Collector `0.3.0`;
- FEATURE-01 `0.1.0`;
- FEATURE-02 `0.2.0`;
- FEATURE-03 `0.3.0`;
- Analytics `analytics_0.1.0`;
- Expert `expert_0.7.0`;
- Match Rating `match_rating_v0.5-candidate`;
- Performance Index `performance_score_v0.2-experimental`;
- GPS summary `gps_physical_summary_v0.1-descriptive`;
- Attention `attention_flags_v0.3-auditable`;
- Reports schema `0.7.0`.

Fuente:
- catálogos y `PROJECT_STATE.md`.

---

## Tabla 3 — Familias del sistema experto

Columnas:
- nodo;
- propósito;
- fuente de evidencia;
- tipo de salida;
- limitación principal.

Especialmente indicar:
- N9000: solo GPS observado no sintético;
- N13000: policy no validada → recomendación no emitida.

---

## Tabla 4 — Resultados del QA global

Filas:
- Data/Core;
- Feature Engine;
- Analytics;
- Expert;
- Dashboard;
- Access control;
- LLM;
- Reports;
- Publication/demo.

Columnas:
- gate;
- resultado;
- evidencia/validator.

Fuente:
- `PROJECT_STATE.md`;
- `docs/TFM_EVIDENCE_MATRIX.md`.

---

## Tabla 5 — Match Rating V5: cobertura

Datos ya documentados:

```text
rated appearances = 590/590
matches = 38/38
outfield PERF18_ANCHORED = 380
GK route = 38
generic role fallback = 172
nulls = 0
duplicates = 0
out_of_range = 0
```

Fuente:
- contrato/validators de Match Rating;
- `PROJECT_STATE.md`.

Interpretación permitida:
- cobertura técnica del rating.

No interpretar como validez externa universal.

---

## Tabla 6 — Demo sintética pública reproducible

Datos:

```text
matches = 12
players = 18
player_match = 216
played = 192
FEATURE-01 = 6048
FEATURE-02 = 42336
FEATURE-03 = 30456
analytics_rows = 12096
expert_rows = 39960
N13000 = 648
ratings = 192
performance_index = 192
gps = 192
professional_source_rows = 0
```

Fuente:
- `publication/validate_synthetic_demo.py`.

---

## Tabla 7 — Limitaciones y mitigaciones

Filas recomendadas:

| Limitación | Consecuencia | Mitigación actual | Trabajo futuro |
|---|---|---|---|
| Sin validación con entrenadores | no se demuestra utilidad causal | claims limitados a viabilidad | estudio con usuarios |
| Sin GPS real en experto | N9000 sin evidencia observada actual | degradación explícita | piloto GPS real |
| Performance Index experimental | no debe tratarse como verdad objetiva | etiqueta experimental | validación externa |
| N13000 sin policy validada | no hay recomendación táctica automática | safe gate | ground truth + policy |
| Auth real ausente | no es SaaS productivo completo | access-control structural | proveedor identidad |
| Dataset profesional no redistribuible | no publicable | demo sintética | licencia/open data |
| Collector sin estudio multiobservador propio | fiabilidad humana no demostrada | contratos funcionales | estudio inter/intra-observer |

---

# 3. Anexos recomendados

## Anexo A — Taxonomía completa del Collector

Fuente directa:
- `collector/event_catalog.json`.

No copiar código JavaScript innecesario.

## Anexo B — Diccionario de datos

Fuente:
- schema + migrations + `data/README.md`.

## Anexo C — Feature catalog

Fuente:
- `features/catalog.json`;
- catálogos temporales.

## Anexo D — Sistema experto

Incluir:
- listado de familias;
- ejemplos representativos de nodo;
- no volcar 154k decisiones en la memoria.

## Anexo E — Gates y QA

Incluir salidas compactas de validators relevantes.

## Anexo F — Reproducibilidad

Incluir:

```powershell
git clone ...
python -m pip install -r requirements.txt
python -m publication.validate_synthetic_demo --rebuild
```

más referencia a GitHub Actions.

## Anexo G — Coach Copilot

Incluir:
- arquitectura;
- preguntas soportadas;
- guardrails;
- ejemplos de respuesta grounded;
- limitaciones no soportadas.

---

# 4. Orden visual recomendado en la memoria

```text
Introducción
→ Figura 1 arquitectura

Marco teórico
→ sin sobrecargar de figuras propias

Metodología
→ Figuras 3, 4, 5, 6 y 8
→ Tablas 1, 2 y 3

Producto
→ Figuras 7 y 9

Validación/resultados
→ Figura 10
→ Tablas 4, 5 y 6

Limitaciones
→ Tabla 7

Anexos
→ detalle técnico reproducible
```

---

# 5. Regla de producción

Antes de insertar cualquier captura, gráfico o tabla final:

1. identificar su fuente exacta;
2. generar el valor automáticamente cuando sea posible;
3. conservar el script o consulta que lo produce;
4. no mezclar caso profesional con demo sintética sin etiquetarlo;
5. no presentar un gráfico descriptivo como validación causal;
6. registrar la figura final en la matriz de evidencias si sostiene un claim importante.
