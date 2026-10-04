# Football Performance System

Sistema de análisis de rendimiento futbolístico para equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos observables de vídeo y GPS opcional en información estructurada, auditable y utilizable por un cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster en **Data Science e Inteligencia Artificial**. El producto principal es una aplicación web funcional; los PDF y el asistente IA son capas downstream sobre analytics ya calculados.

## Hipótesis del TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

El prototipo actual contrasta favorablemente la **viabilidad técnica y arquitectónica** de esta hipótesis.

No demuestra que el sistema mejore causalmente las decisiones de un entrenador, el rendimiento deportivo ni la prevención de lesiones.

---

## Estado actual

```text
GLOBAL END-TO-END QA            PASS
PUBLIC SYNTHETIC DEMO           PASS
REPRODUCIBILITY                 PASS
CI AUTOMÁTICO                   PASS
COACH COPILOT LOCAL REAL        PASS 28/28 · avg 0.4s
OPENAI BYOK CONTRACT            PASS
```

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
```

Taxonomía congelada:

```text
event_catalog v0.3.0
```

Registra hechos observables y contexto de partido; no calcula métricas avanzadas.

Incluye:
- partido, equipo, rival, fecha y formación;
- jugador, dorsal, titular/suplente y minutos;
- rol, lado y cambios de rol;
- pase normal/largo/centro con éxito/fallo;
- pase clave y asistencia;
- regates y pérdidas;
- remates con outcomes exclusivos;
- entrada, intercepción, bloqueo y despeje;
- faltas con localización;
- tarjetas y penaltis;
- córners/ABP y resultado de secuencia;
- portero: parada y gol encajado;
- exportación estructurada y autosave.

No recoge manualmente xG, PPDA, posesión avanzada, pressing, heatmaps, fatiga ni métricas derivables.

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

---

## Match Rating y Performance Index

### Match Rating V5

```text
match_rating_v0.5-candidate
coverage=590/590 en el caso profesional de desarrollo
```

Valoración inmediata jugador-partido. Está congelado: no se modifica sin nueva evidencia, experimento explícito y validación.

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

---

## Modos del producto

- **Team Mode**: estado del equipo, plantilla, forma, participación, ratings, tendencias y evidencia.
- **Player Mode**: perfil individual, evolución, rol observado, expert system, GPS y PDF.
- **Match Mode**: ratings, minutos, roles, observaciones deterministas, GPS y PDF.
- **Físico / GPS**: capa descriptiva opcional separada de las decisiones críticas.
- **Calidad y alertas**: cobertura, limitaciones y atención de datos.
- **Asistente IA**: consultas en lenguaje natural sobre resultados estructurados.
- **Rival Mode**: extensión futura; el sistema principal no depende de datos del rival.

---

## Coach Copilot

El asistente ya no depende de que un LLM interprete todas las preguntas.

### Runtime local final

```text
pregunta
→ router determinista de alta confianza
→ tools Python read-only
→ DuckDB / analytics / expert system
→ respuesta factual determinista
```

Solo si la intención sigue siendo ambigua:

```text
pregunta ambigua
→ qwen3.5:4b
→ selección semántica de tool
→ tools Python read-only
→ DuckDB / analytics / expert system
→ evidencia estructurada
→ respuesta factual
```

El LLM no tiene acceso directo a DuckDB y no recalcula Match Rating, Performance Index, rankings ni decisiones expertas.

Validación local real final con DuckDB profesional:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
```

El smoke cubre rankings, ventanas temporales, perfiles, GPS, comparaciones entre jugadores y por posición, partidos, calidad de datos, guardrails, ruido/fuera de dominio y follow-ups. En esta validación final todos los casos se resolvieron con `rounds=0`.

Smoke reproducible:

```powershell
python llm\smoke_test_coach_agent.py
```

### OpenAI opcional con clave del usuario

La misma página del asistente permite seleccionar:

```text
Local · Qwen
OpenAI API · clave propia
```

En modo OpenAI:
- las preguntas claras siguen siendo deterministas y no consumen API;
- solo el lenguaje ambiguo puede usar OpenAI como router semántico;
- OpenAI únicamente puede pedir tools FPS bounded/read-only;
- cada tool call se revalida localmente;
- DuckDB sigue siendo consultado por Python, no por el modelo;
- la API key pertenece al usuario y la UI no la persiste en DuckDB ni en archivos del proyecto;
- los mismos guardrails deportivos siguen activos.

Estado:

```text
implementación                     PASS
unit / contract tests              PASS
synthetic demo CI                  PASS
live call con API key real         NO VALIDADA AÚN
```

La conexión inversa `ChatGPT → FPS` mediante MCP no forma parte del MVP actual.

### Límites explícitos

El asistente no debe inventar ni afirmar sin policy validada:
- fatiga o readiness;
- riesgo de lesión;
- XI ideal o quién debe ser titular;
- recomendación táctica automática;
- `mejor jugador`, `más completo` o `más determinante` sin una métrica analítica aprobada.

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

## Ejecutar el caso local de desarrollo

```powershell
$env:FPS_DB_PATH="D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
$env:FPS_LOCAL_LLM_MODEL="qwen3.5:4b"
streamlit run app\streamlit_app.py
```

Para usar fallback semántico local se necesita Ollama y el modelo configurado. Las consultas deterministas siguen funcionando aunque Ollama no esté disponible.

---

## CI automático

Workflow:

```text
.github/workflows/tests.yml
```

Pipeline:

```text
Ubuntu limpio
→ Python 3.13
→ instalar dependencias
→ pytest -q
→ construir demo sintética
→ validar demo end-to-end
→ validar Coach Copilot query-space contract
```

Runs recientes de referencia:

```text
37167083614 = SUCCESS — query-space + preflight contract
37167157174 = SUCCESS — final code gate before local 28-case smoke
```

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
- [`docs/TFM_MANUSCRIPT_DRAFT.md`](docs/TFM_MANUSCRIPT_DRAFT.md) — manuscrito integrado;
- [`docs/TFM_EVIDENCE_MATRIX.md`](docs/TFM_EVIDENCE_MATRIX.md) — claims y evidencias;
- [`docs/TFM_METHODOLOGY_DRAFT.md`](docs/TFM_METHODOLOGY_DRAFT.md) — metodología;
- [`docs/TFM_RESULTS_DRAFT.md`](docs/TFM_RESULTS_DRAFT.md) — resultados;
- [`docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md`](docs/TFM_DISCUSSION_CONCLUSIONS_DRAFT.md) — discusión y conclusiones;
- [`docs/TFM_SCREENSHOT_CHECKLIST.md`](docs/TFM_SCREENSHOT_CHECKLIST.md) — capturas de entrega;
- [`docs/TFM_SUBMISSION_CHECKLIST.md`](docs/TFM_SUBMISSION_CHECKLIST.md) — checklist final;
- [`publication/README.md`](publication/README.md) — demo y reproducibilidad.

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

El núcleo funcional está cerrado. Prioridad inmediata:

```text
1  Revisión visual final del Coach Copilot
2  Capturas canónicas del producto
3  Sincronización final del manuscrito con la arquitectura actual
4  Checklist de entrega
5  Maquetación / defensa / demo final
```

Criterio de cierre:

> **producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
