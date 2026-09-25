# Football Performance System

Sistema de análisis de rendimiento futbolístico orientado a equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos realistas de vídeo y GPS opcional en información estructurada para el cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster, pero el objetivo es un **producto funcional, auditable y publicable**, no solo una memoria académica.

## Estado actual

La infraestructura técnica base está avanzada y validada: Collector, DuckDB, Feature Engine, baseline experto N1000-N13000, dashboard Streamlit, assistant con guardrails, generación PDF y tooling de anonimización.

Sin embargo, dashboard, reporting y assistant se consideran todavía **prototype v0.1**, no producto final. El backend está más avanzado que la capa de producto y falta cerrar la capa Analytics que convertirá features en insights estructurados.

El proyecto ha pasado a un flujo **architecture-first + gated** para evitar seguir añadiendo parches de interfaz antes de cerrar las decisiones estructurales.

Documentos de control:

- [`PROJECT_STATE.md`](PROJECT_STATE.md) — estado operativo y siguiente paso;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura vigente;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — fases, agentes y condiciones de desbloqueo;
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones estructurales y gates.

## Arquitectura

```text
CAPTURE / IMPORT
        ↓
RAW + NORMALIZED DATA
        ↓
FEATURE ENGINE
        ↓
ANALYTICS ENGINE
        ↓
DECISION ENGINE
        ↓
PRODUCT SERVICE LAYER
        ↓
WEB / REPORTS / AI ASSISTANT
        ↓
QA / PUBLICATION
```

La regla central es que una capa superior no puede inventar métricas, rankings, evaluaciones o recomendaciones que no existan en una capa inferior validada.

## Orden de desarrollo vigente

```text
ARCHITECTURE-01
        ↓
ANALYTICS-01
        ↓
DECISION POLICY / N13000
        ↓
PRODUCT UX
        ↓
REPORTS-02
        ↓
ASSISTANT ARCHITECTURE
        ↓
ML si aporta valor
        ↓
FINAL PRODUCT / PUBLICATION / TFM
```

## Modos del producto

- **Team Mode** — modo principal;
- **Player Mode** — análisis individual;
- **Match View** — contexto y lectura de partido;
- **Rival Mode** — extensión futura, no necesaria para el sistema principal.

La versión final de la web será **insight-first**: conclusiones/evidencias primero y tablas como segundo nivel de detalle/auditoría.

## Principios metodológicos

- priorizar variables recogibles en fútbol amateur;
- separar raw data, features, analytics, decisiones y explicación;
- evitar data leakage;
- no inferir datos ausentes silenciosamente;
- no crear scores, rankings, pesos o umbrales sin validación;
- GPS opcional;
- ninguna conclusión importante depende exclusivamente de un LLM;
- cada regla del sistema experto conserva `entrada → condición → resultado → confianza → justificación`;
- no emitir recomendación final N13000 mientras no exista una policy validada.

## Baseline técnico actual

### Data / Collector

DuckDB con unidad principal `player_match`. Collector HTML funcional. GPS normalization multi-proveedor preparada.

### Feature Engine

FEATURE-01/02/03 validadas como baseline determinista y temporal leakage-safe, incluyendo historial condicionado a rol observado.

### Decision Engine

Baseline experto N1000-N13000 (`expert_0.7.0`) validado y auditable. N13000 mantiene estados `RECOMMENDATION_NOT_ISSUED_*` hasta validar la policy final.

### Dashboard

Streamlit TEAM / PLAYER / MATCH / ASSISTANT funciona técnicamente, pero la UX actual es demasiado tabular y se rediseñará después de ANALYTICS-01.

### Assistant

Existe un prototipo seguro con fallback determinista y proveedor OpenAI opcional. La arquitectura final local/cloud/híbrida todavía no está cerrada.

### Reports

Los PDF Team / Player / Match se generan y cumplen los guardrails, pero se consideran prueba técnica. REPORTS-02 definirá informes profesionales basados en los mismos insights que la web.

## Instalación local del prototipo

```powershell
git clone <URL_DEL_REPOSITORIO>
cd football-performance-system
python -m pip install -r requirements.txt
streamlit run app\streamlit_app.py
```

También puede indicarse otra base DuckDB:

```powershell
$env:FPS_DB_PATH = "C:\ruta\a\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

## Demo y publicación

`publication/validate_public_demo.py` genera y valida una copia local anonimizada del caso de desarrollo.

La anonimización técnica no implica derecho de redistribución. Si la fuente profesional no permite publicar los datos, el repositorio final utilizará un dataset sintético o con licencia compatible.

## Estructura principal

```text
football-performance-system/
├── collector/
├── data/
├── gps/
├── features/
├── decision_tree/
├── models/
├── llm/
├── app/
├── reports/
├── publication/
├── tests/
├── docs/
├── examples/
├── README.md
└── PROJECT_STATE.md
```

## Gobernanza del proyecto

GitHub es la memoria técnica definitiva. Un nuevo chat o agente debe consultar primero `PROJECT_STATE.md`, después `docs/ARCHITECTURE.md`, `docs/WORKFLOW.md` y, si existe un gate abierto, `docs/DECISIONS.md`.

Las decisiones técnicas ordinarias se delegan al Architect/Integrator. El usuario solo interviene en gates con impacto real sobre arquitectura, significado deportivo, política de recomendación, UX principal, privacidad/LLM o publicación.
