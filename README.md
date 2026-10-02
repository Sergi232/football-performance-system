# Football Performance System

Sistema de análisis de rendimiento futbolístico orientado a equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos de vídeo y GPS opcional en información estructurada, auditable y útil para el cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster en **Data Science e Inteligencia Artificial**. El entregable principal es doble: un producto funcional y una metodología defendible en datos, feature engineering, analytics, sistema experto, validación, experimentación DS/ML y explicabilidad.

La aplicación web y este repositorio son el producto principal. Los PDF son entregables técnicos complementarios.

## Hipótesis del TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

El prototipo actual contrasta favorablemente la **viabilidad técnica y arquitectónica** de esta hipótesis. No demuestra que el sistema mejore causalmente las decisiones de un entrenador, el rendimiento deportivo o la prevención de lesiones.

## Estado actual

El núcleo funcional está construido y validado.

```text
GLOBAL END-TO-END QA: PASS
```

Cadena validada:

```text
Collector
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
→ Public-demo anonymization
```

Estado resumido:
- Data Layer DuckDB con unidad principal `player_match`;
- Data Collector HTML V1.1 cerrado y oficial;
- taxonomía `event_catalog v0.3.0` congelada;
- normalización GPS multi-proveedor validada;
- GPS sintético demo `gps_synthetic_demo_v1.2.0` validado y explícitamente etiquetado;
- resumen físico `gps_physical_summary_v0.1-descriptive`;
- Feature Engine FEATURE-01/02/03 validado;
- Analytics Engine validado;
- sistema experto `expert_0.7.0` N1000-N13000 validado;
- Match Rating V5 activo y congelado;
- Performance Index histórico/posicional experimental;
- Attention Centre auditable;
- dashboard Streamlit Team / Player / Match / Físico-GPS / Asistente;
- Coach Copilot local mediante Ollama y tools Python read-only;
- informes PDF Team / Player / Match V6;
- anonimización demo y control de acceso estructural;
- temporada de demostración: 38 partidos y 590 apariciones jugador-partido.

Fuente de verdad operativa: [`PROJECT_STATE.md`](PROJECT_STATE.md).

## Documentación clave

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura vigente;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — flujo actual;
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones estructurales;
- [`docs/DATA_SCIENCE_AI_STRATEGY.md`](docs/DATA_SCIENCE_AI_STRATEGY.md) — estrategia académica DS/IA;
- [`docs/MATCH_RATING_PRODUCT_CONTRACT.md`](docs/MATCH_RATING_PRODUCT_CONTRACT.md) — contrato Match Rating V5;
- [`dsai/README.md`](dsai/README.md) — experimentación DS/ML;
- [`collector/COLLECTOR_MVP.md`](collector/COLLECTOR_MVP.md) — Collector V1.1;
- [`gps/README.md`](gps/README.md) — GPS normalizado/demo;
- [`publication/README.md`](publication/README.md) — anonimización/publicación.

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

Regla central: **una capa superior no puede inventar cálculos, métricas, scores, rankings o recomendaciones que no existan en una capa inferior validada**.

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
4 collector contract tests: PASS
```

## Rendimiento

### Match Rating V5

```text
match_rating_v0.5-candidate
```

Valoración inmediata `jugador-partido`, disponible desde el primer partido.

Contrato validado:

```text
played_rows=590
rated_rows=590
rating_coverage=1.0000
matches=38
goalkeeper_rows=38
generic_role_rows=172
first_match_rated_rows=16
MATCH RATING CONTRACT: PASS
```

Características:
- contexto posicional CB / FB / DM / CM / AM / W / ST;
- anchors explícitos y auditables;
- ruta separada de portero;
- portero: 90% shot-stopping / 10% distribución;
- fallback genérico cuando no existe rol fiable;
- no inventa posición;
- sin castigo global automático por resultado del equipo;
- GPS no modifica el rating.

V5 está congelado. No se cambia sin nueva evidencia, experimento explícito y validación.

### Performance Index

```text
performance_score_v0.2-experimental
```

Capa histórica/posicional complementaria para evolución, forma, consistencia y contexto de rol. No sustituye al Match Rating.

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
N10000  rol y encaje
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

Cada salida conserva:

```text
input → condition → result → confidence → justification
```

N13000 no emite recomendación táctica sin policy validada.

GPS sintético no cuenta como evidencia física observada en N9000.

## Modos del producto

### Team Mode

Modo principal: estado del equipo, plantilla, forma, evolución, participación, tendencias, Match Rating, Performance Index, expert y GPS descriptivo.

### Player Mode

Perfil individual con Match Ratings, Performance Index, dimensiones, evolución, rol observado, expert, GPS y PDF V6.

### Match Mode

Operativo desde el primer partido: ratings, confianza, minutos, roles, dimensiones, observaciones deterministas, GPS y PDF V6.

### Físico / GPS

GPS es opcional.

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
GPS real > GPS sintético
```

No existen umbrales canónicos de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

Demo actual:

```text
generator_version=gps_synthetic_demo_v1.2.0
observations=38197
summary_rows=590
latest_rows=590
```

### Coach Copilot

Arquitectura vigente:

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

El LLM no accede directamente a DuckDB y no recalcula Match Rating, Performance Index, features críticas ni decisiones expertas.

Perfil local validado:

```text
model=qwen3:1.7b
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=18
keep_alive=30m
LOCAL AGENT CONTRACT: PASS (4/4)
```

El warm-up del validator usa el mismo `num_ctx` que producción para evitar recarga del runner/model context en CPU.

### Rival Mode

Extensión futura. El sistema principal no depende de datos del rival.

## DS / ML experimental

Experimentos documentados:
- change detection → experimental / no deploy;
- player similarity → exploratorio / no deploy;
- role/source-position classification → context-only / no deploy.

La robustez pre-match mostró que un baseline simple basado en historial posicional superaba al enfoque ML en esta muestra. No se fuerza un modelo complejo si una regla simple funciona mejor.

`role_player_fit`, Expert-vs-ML y calibración final N13000 siguen bloqueados sin ground truth independiente defendible.

## Informes PDF V6

Capa activa:

```text
reports/report_metrics.py          → report_descriptive_v0.2
reports/data_builder.py            → schema 0.7.0
reports/pdf_engine_elite_v6.py     → Team / Player / Match
reports/pdf_engine_es.py           → wrapper app
```

Estado:

```text
REPORTS ELITE TECHNICAL GATE V6: PASS
Team PDF   = 4 páginas
Player PDF = 3 páginas
Match PDF  = 3 páginas
```

Los PDF consumen analytics materializados y no recalculan lógica crítica.

## Principios metodológicos

- variables realistas para fútbol amateur;
- raw / features / analytics / decision / LLM separados;
- temporal leakage control;
- ningún claim importante depende exclusivamente del LLM;
- no inventar scores, thresholds, rankings o pesos;
- no crear targets ML circulares;
- baseline simple antes de modelo complejo;
- GPS opcional y explícitamente etiquetado si es sintético;
- Team Mode no depende de datos del rival;
- no inventar validación con entrenadores/usuarios/clientes.

## Instalación local

```powershell
git clone <URL_DEL_REPOSITORIO>
cd football-performance-system
python -m pip install -r requirements.txt
```

La aplicación necesita una DuckDB compatible. Durante el desarrollo la DB profesional permanece local y no se redistribuye por defecto.

Ruta por variable de entorno:

```powershell
$env:FPS_DB_PATH = "C:\ruta\a\football_performance.duckdb"
$env:FPS_DEMO_MODE = "1"
streamlit run app\streamlit_app.py
```

## QA principal

El QA global se cerró el 03/10/2026:

```text
Fase 1 — Data/core                PASS
Fase 2 — Analytics/Expert         PASS
Fase 3A — Product                 PASS
Fase 3B — Delivery                PASS
GLOBAL END-TO-END QA              PASS
```

Incluye Collector, DB, FEATURE-01/02/03, Analytics, Match Rating, GPS, Expert N1000-N13000, Dashboard, UI, Access Control, Attention Centre, Match Mode, Assistant, Coach Copilot, Reports y anonimización demo.

## Publicación y datos

Durante desarrollo se han utilizado datos profesionales PannaData/Opta para validación. Esa fuente no define las variables del producto amateur y no se redistribuye automáticamente.

Estado de anonimización local:

```text
PUBLICATION-01 ANONYMIZED DEMO CONTRACT: PASS
REDISTRIBUTION STATUS: NOT CLEARED
```

Anonimizar nombres no concede derechos de publicación. Si la licencia no permite redistribución, el paquete público deberá usar un dataset sintético reproducible o un dataset abierto con licencia compatible.

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

## Prioridad actual

El núcleo funcional no se reconstruye salvo incidencia concreta o nueva evidencia.

```text
1  Documentation sync
2  Reproducibility package
3  Validator path consistency
4  Reactivar CI push/PR
5  Memoria / README de entrega
6  Defensa / demo final
```

Criterio de cierre:

**producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
