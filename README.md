# Football Performance System

Sistema de análisis de rendimiento futbolístico orientado a equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos observables de vídeo y GPS opcional en información estructurada, auditable y utilizable por un cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster en **Data Science e Inteligencia Artificial**. El producto principal es una aplicación web funcional; los PDF y el asistente IA son capas complementarias sobre analytics ya calculados.

## Hipótesis del TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

El prototipo actual contrasta favorablemente la **viabilidad técnica y arquitectónica** de esta hipótesis.

No demuestra que el sistema mejore causalmente las decisiones de un entrenador, el rendimiento deportivo ni la prevención de lesiones.

---

## Estado actual

```text
GLOBAL END-TO-END QA        PASS
PUBLIC SYNTHETIC DEMO       PASS
REPRODUCIBILITY             PASS
CI AUTOMÁTICO               PASS
```

Cadena validada:

```text
Collector / Import + GPS opcional
→ DuckDB
→ Features
→ Analytics
→ Match Rating
→ GPS
→ Expert N1000-N13000
→ Dashboard
→ Access control
→ Demo presentation
→ Coach Copilot
→ PDF
```

Estado resumido:

- Data Collector HTML V1.1 cerrado y oficial;
- taxonomía `event_catalog v0.3.0` congelada;
- Data Layer DuckDB con unidad principal `player_match`;
- normalización GPS multi-proveedor validada;
- GPS sintético de integración explícitamente etiquetado;
- Feature Engine FEATURE-01/02/03 validado;
- Analytics Engine validado;
- sistema experto `expert_0.7.0` N1000-N13000 validado;
- Match Rating V5 activo y congelado;
- Performance Index histórico/posicional experimental;
- Attention Centre auditable;
- dashboard Streamlit Team / Player / Match / Físico-GPS / Asistente;
- Coach Copilot local mediante Ollama y tools Python read-only;
- informes PDF Team / Player / Match V6;
- control de acceso estructural;
- demo pública sintética reproducible desde cero;
- GitHub Actions activo en `push` y `pull_request`.

Fuente de verdad operativa: [`PROJECT_STATE.md`](PROJECT_STATE.md).

---

## Arquitectura

```text
COLLECTOR / IMPORT + GPS OPCIONAL
            ↓
RAW / NORMALIZED DATA
            ↓
FEATURE ENGINE
            ↓
ANALYTICS
            ↓
EXPERT SYSTEM / DS-ML
            ↓
PRODUCT SERVICE / ACCESS LAYER
            ↓
WEB DASHBOARD
      ↓             ↓
AI ASSISTANT       PDF
```

Regla central:

> **Una capa superior no puede inventar cálculos, métricas, rankings o recomendaciones que no existan en una capa inferior validada.**

---

## Data Collector V1.1

Entrada oficial:

```text
collector/data_collector_futbol.html
→ collector/data_collector_futbol_v1.html
```

Taxonomía:

```text
event_catalog v0.3.0
```

Registra hechos observables y contexto de partido; no calcula métricas avanzadas.

Incluye:

- partido, equipo, rival, fecha y formación;
- jugador, dorsal editable, titular/suplente, entrada/salida y minutos;
- rol, lado y cambios de rol;
- pase normal/largo/centro con éxito/fallo;
- pase clave y asistencia;
- regates y pérdidas;
- remates con outcomes exclusivos;
- defensa: entrada, intercepción, bloqueo y despeje;
- faltas con x/y;
- tarjetas y segunda amarilla;
- penaltis;
- córners/ABP y resultado de secuencia;
- portero: parada y gol encajado;
- autosave, undo, CSV eventos, CSV resumen y JSON;
- interfaz visible en castellano y responsive.

Estado:

```text
COLLECTOR V1.1 FINAL GATE: PASS
```

---

## Data / Feature / Analytics

La unidad analítica principal es `player_match`.

### FEATURE-01

28 features base deterministas: ratios y normalizaciones per-90 con preservación explícita de `NULL`.

### FEATURE-02

Operadores temporales **strict-past**. Ningún partido actual, de la misma fecha o futuro informa el baseline del registro actual.

### FEATURE-03

Contexto temporal condicionado por el rol observado. El sistema no inventa roles ausentes.

### ANALYTICS-01

Separa:

```text
SELF_ROLE_PRIOR
PEER_ROLE_PRIOR
```

El jugador actual queda excluido del pool de peers y cada peer recibe el mismo peso.

Analytics no crea por sí mismo rankings, recomendaciones ni labels de rendimiento bueno/malo.

---

## Match Rating y Performance Index

### Match Rating V5

```text
match_rating_v0.5-candidate
```

Valoración inmediata jugador-partido, disponible desde el primer partido.

Baseline validado del caso profesional de desarrollo:

```text
played_rows=590
rated_rows=590
rating_coverage=1.0000
matches=38
goalkeeper_rows=38
generic_role_rows=172
```

V5 está congelado. No se modifica sin nueva evidencia, experimento explícito y validación.

### Performance Index

```text
performance_score_v0.2-experimental
```

Capa histórica/posicional complementaria. No sustituye al Match Rating y conserva estado experimental.

---

## Sistema experto

```text
N1000   disponibilidad / actividad
N2000   perfil estructural
N3000   forma / evolución
N4000   amenaza ofensiva
N5000   creación / progresión
N6000   contribución defensiva
N7000   finalización
N8000   contexto del equipo
N9000   componente físico opcional
N10000  rol y contexto
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

Cada salida conserva:

```text
input → condition → result → confidence → justification
```

N13000 **no emite una recomendación táctica** sin una policy previamente validada.

El GPS sintético no cuenta como evidencia física observada en N9000.

---

## GPS opcional

Flujo canónico:

```text
archivo proveedor / demo sintética
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / reports
```

Precedencia:

```text
GPS real observado > GPS sintético
```

No existen umbrales canónicos de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

GPS no modifica Match Rating, Performance Index ni decisiones expertas.

---

## Modos del producto

### Team Mode

Estado del equipo, plantilla, forma, participación, Match Rating, Performance Index, evolución, tendencias descriptivas, evidencia experta y GPS opcional.

### Player Mode

Perfil individual, Match Ratings, Performance Index, dimensiones, evolución, rol observado, expert, GPS y PDF.

### Match Mode

Operativo desde el primer partido: ratings, confianza, minutos, roles, observaciones deterministas, GPS y PDF.

### Físico / GPS

Capa descriptiva opcional y separada de las decisiones deportivas críticas.

### Rival Mode

Extensión futura. El sistema principal no depende de datos del rival.

---

## Coach Copilot

Arquitectura:

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ router determinista
→ compact evidence
→ Ollama qwen3:1.7b
→ semantic guard
→ Coach Copilot
```

MVP oficial: castellano.

Perfil local validado:

```text
model=qwen3:1.7b
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=18
keep_alive=30m
LOCAL AGENT CONTRACT: PASS (4/4)
```

El LLM no accede directamente a DuckDB y no recalcula Match Rating, Performance Index, features críticas ni decisiones expertas.

---

## Informes PDF V6

```text
Team PDF   = 4 páginas
Player PDF = 3 páginas
Match PDF  = 3 páginas
```

Los PDF consumen analytics materializados y no recalculan lógica crítica.

```text
REPORTS ELITE TECHNICAL GATE V6: PASS
```

---

## Demo pública sintética reproducible

La base profesional utilizada durante desarrollo permanece fuera del repositorio y no se redistribuye automáticamente.

Para permitir una demo pública reproducible se genera una DuckDB **100% sintética desde cero**:

```powershell
python -m publication.validate_synthetic_demo --rebuild
```

Gate validado:

```text
SYNTHETIC PUBLIC DEMO CONTRACT: PASS
matches=12
players=18
player_match=216
played=192
professional_source_rows=0
app_read_layer=PASS
report_payloads=PASS
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

La demo sintética reutiliza el código real del proyecto para Features, Analytics, Expert System, GPS y capas de producto.

Match Rating V5 y Performance Index de esta demo son fixtures sintéticos de compatibilidad de UI/producto. No representan una revalidación científica del modelo calibrado en el caso profesional.

Más detalle: [`publication/README.md`](publication/README.md).

---

## Ejecutar la demo pública desde un clone limpio

```powershell
git clone <URL_DEL_REPOSITORIO>
cd football-performance-system
python -m pip install -r requirements.txt
python -m publication.validate_synthetic_demo --rebuild

$env:FPS_DB_PATH="$PWD\data\football_performance_synthetic_demo.duckdb"
$env:FPS_DEMO_MODE="1"
streamlit run app\streamlit_app.py
```

No se necesita la DuckDB profesional para esta demo.

---

## CI automático

Workflow:

```text
.github/workflows/tests.yml
```

Se ejecuta automáticamente en:

```text
push
pull_request
workflow_dispatch
```

Pipeline:

```text
Ubuntu limpio
→ Python 3.13
→ instalar dependencias
→ pytest -q
→ construir demo sintética
→ validar demo end-to-end
```

Ejecución validada:

```text
GitHub Actions run 37081464123
Unit and contract tests: PASS
Synthetic public demo: PASS
Conclusion: SUCCESS
```

Esto verifica que el repositorio funciona fuera del ordenador de desarrollo.

---

## Principios metodológicos

- variables realistas para fútbol amateur;
- raw / features / analytics / decision / LLM separados;
- control explícito de temporal leakage;
- ningún claim importante depende exclusivamente del LLM;
- no inventar scores, thresholds, rankings o pesos;
- no crear targets ML circulares;
- baseline simple antes de modelo complejo;
- GPS opcional y explícitamente etiquetado si es sintético;
- Team Mode no depende de datos del rival;
- no inventar validación con entrenadores, usuarios o clientes.

---

## DS / ML experimental

Experimentos documentados:

- change detection → experimental / no deploy;
- player similarity → exploratorio / no deploy;
- role/source-position classification → context-only / no deploy.

La robustez pre-match mostró que un baseline simple basado en historial posicional superaba al enfoque ML en esa muestra. No se fuerza un modelo complejo si una regla simple funciona mejor.

`role_player_fit`, Expert-vs-ML y calibración final N13000 siguen bloqueados sin ground truth independiente defendible.

---

## Límites del proyecto

No está validado afirmar que el sistema:

- mejora causalmente las decisiones del entrenador;
- aumenta rendimiento, puntos o victorias;
- detecta fatiga o readiness;
- estima riesgo de lesión;
- recomienda un XI ideal;
- predice automáticamente el rol táctico óptimo;
- dispone de validación comercial real.

La autenticación completa de producción tampoco forma parte del MVP actual.

---

## Documentación clave

- [`PROJECT_STATE.md`](PROJECT_STATE.md) — fuente de verdad operativa;
- [`docs/TFM_MEMORIA_BASE.md`](docs/TFM_MEMORIA_BASE.md) — borrador técnico de la memoria;
- [`docs/TFM_EVIDENCE_MATRIX.md`](docs/TFM_EVIDENCE_MATRIX.md) — claims y evidencias;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura vigente;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — flujo actual;
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones estructurales;
- [`docs/DATA_SCIENCE_AI_STRATEGY.md`](docs/DATA_SCIENCE_AI_STRATEGY.md) — estrategia DS/IA;
- [`docs/MATCH_RATING_PRODUCT_CONTRACT.md`](docs/MATCH_RATING_PRODUCT_CONTRACT.md) — Match Rating V5;
- [`dsai/README.md`](dsai/README.md) — experimentación DS/ML;
- [`collector/COLLECTOR_MVP.md`](collector/COLLECTOR_MVP.md) — Collector V1.1;
- [`gps/README.md`](gps/README.md) — GPS;
- [`publication/README.md`](publication/README.md) — publicación y reproducibilidad.

---

## Estructura

```text
football-performance-system/
├── analytics/
├── app/
├── collector/
├── data/
├── decision_tree/
├── docs/
├── dsai/
├── features/
├── gps/
├── llm/
├── product/
├── publication/
├── reports/
├── tests/
├── README.md
└── PROJECT_STATE.md
```

---

## Fase actual

El núcleo funcional no se amplía salvo incidencia concreta o nueva evidencia.

Prioridad:

```text
1  Memoria académica definitiva
2  Matriz de evidencias / resultados
3  Revisión final del repositorio
4  Defensa y demo final
```

Criterio de cierre:

> **producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
