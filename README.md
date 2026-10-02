# Football Performance System

Sistema de análisis de rendimiento futbolístico orientado a equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos de vídeo y GPS opcional en información estructurada, auditable y útil para el cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster en **Data Science e Inteligencia Artificial**. El entregable principal es doble: un producto funcional y reproducible, y una metodología defendible en datos, feature engineering, analytics, sistema experto, validación, DS/ML experimental y explicabilidad.

La aplicación web y este repositorio son el producto principal. Los PDF son entregables técnicos complementarios.

## Hipótesis del TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

El prototipo actual permite contrastar favorablemente la **viabilidad técnica y arquitectónica** de esta hipótesis. No demuestra todavía que el sistema mejore causalmente las decisiones de un entrenador, el rendimiento deportivo o la prevención de lesiones.

## Estado actual

El núcleo analítico principal está construido y validado. La fase activa es **FINAL PRODUCT**.

Estado resumido:

- Data Layer DuckDB con unidad principal `player_match`;
- Data Collector HTML funcional, pendiente de simplificación UX, castellano completo y mobile-first;
- normalización GPS multi-proveedor validada estructuralmente;
- GPS demo sintético canónico validado, explícitamente etiquetado y subordinado a GPS real;
- resumen físico descriptivo `gps_physical_summary_v0.1-descriptive` validado;
- Feature Engine determinista y temporal leakage-safe;
- Analytics Engine validado;
- sistema experto auditable N1000-N13000, `expert_0.7.0`;
- Match Rating V5 activo y validado;
- Performance Index histórico/posicional todavía experimental;
- Attention Centre auditable;
- dashboard Streamlit con Home / Team / Player / Match / Físico-GPS / Asistente;
- Coach Copilot local mediante Ollama y tools Python read-only;
- informes PDF Team / Player / Match V6 con GPS descriptivo;
- anonimización de demo y control de acceso estructural;
- producto principal operativo sobre una temporada de demostración de 38 partidos y 590 apariciones jugador-partido.

El estado operativo exacto, versiones vigentes, gates, decisiones y siguiente paso están en [`PROJECT_STATE.md`](PROJECT_STATE.md).

Documentación clave:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura y contratos;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — flujo de trabajo actual;
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones estructurales;
- [`docs/DATA_SCIENCE_AI_STRATEGY.md`](docs/DATA_SCIENCE_AI_STRATEGY.md) — estrategia académica DS/IA;
- [`dsai/README.md`](dsai/README.md) — experimentación DS/ML;
- [`product/README.md`](product/README.md) — Product Spiral;
- [`publication/README.md`](publication/README.md) — publicación y datos demo.

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
EXPERT SYSTEM / ML
            ↓
PRODUCT SERVICE / ACCESS LAYER
            ↓
WEB DASHBOARD
      ↓             ↓
AI ASSISTANT       PDF
```

Regla arquitectónica principal: **una capa superior no puede inventar cálculos, métricas, scores, clasificaciones o recomendaciones que no existan en una capa inferior validada**.

## Rendimiento

### Match Rating

Versión activa:

```text
match_rating_v0.5-candidate
```

Es una valoración inmediata `jugador-partido`, disponible desde el primer partido y sin necesidad de historial.

Características principales:

- modelo posicional para jugadores de campo: CB / FB / DM / CM / AM / W / ST;
- referencias profesionales pre-temporada para normalización/validación;
- anchors decisivos explícitos y auditables;
- modelo separado para porteros;
- portero: 90% shot-stopping / 10% distribución;
- fallback explícito cuando no existe rol fiable;
- nunca se inventa una posición;
- sin castigo global automático por resultado del equipo.

La versión V5 está congelada como baseline vigente. No se modifican fórmula, pesos o arquitectura sin evidencia nueva, experimentación explícita y validación.

### Performance Index

No es el Match Rating.

```text
MATCH RATING
= rendimiento jugador-partido inmediato

PERFORMANCE INDEX
= capa histórica/posicional
= evolución + forma + consistencia + contexto de rol
```

El Performance Index continúa siendo una capa experimental susceptible de mejora posterior.

## Modos del producto

### Team Mode

Modo principal. Resume estado del equipo, plantilla, forma, evolución, distribución del rendimiento, participación, tendencias, contexto técnico y GPS descriptivo opcional.

### Player Mode

Perfil individual con Match Ratings, Performance Index, dimensiones, evolución, historial, rol observado, componente técnico, motor experto, físico opcional y PDF individual V6.

### Match Mode

Operativo desde el primer partido. Incluye ratings, confianza, minutos, roles, dimensiones, observaciones postpartido, GPS descriptivo y PDF V6.

### Físico / GPS

Capa descriptiva y opcional. El producto funciona sin GPS.

Flujo actual:

```text
archivo proveedor / demo sintética
→ gps_imports
→ gps_player_map
→ gps_observations
→ player_match_gps_summary
→ dashboard / informes
```

Regla de precedencia:

```text
GPS real > GPS sintético
```

No se exponen HSR, sprint, workload, fatiga, readiness/disponibilidad física o riesgo de lesión sin definición y validación explícitas.

### Assistant

Coach Copilot local sobre resultados estructurados.

Arquitectura actual:

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ Ollama localhost
→ Coach Copilot
→ entrenador
```

El LLM no recibe acceso directo a DuckDB y no recalcula Match Rating, features críticas ni decisiones expertas. Puede interpretar preguntas abiertas, consultar tools, explicar evidencia, resumir y comparar descriptivamente.

OpenAI no es necesario para el flujo actual; puede permanecer desacoplado como provider opcional, sin dependencia del núcleo analítico.

### Rival Mode

Extensión futura. El sistema principal no depende de datos del rival.

## Sistema experto

Jerarquía actual:

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

Cada resultado conserva:

```text
input → condition → result → confidence → justification
```

No se convierte Match Rating directamente en una recomendación táctica y N13000 no puede emitir una recomendación no validada.

## Principios metodológicos

- Priorizar variables recogibles de forma realista durante un partido amateur.
- Separar raw data, features, analytics, decision engine y explicación final.
- Evitar data leakage; las features temporales usan información estrictamente anterior cuando corresponde.
- No basar conclusiones importantes exclusivamente en un LLM.
- No inventar métricas, scores, rankings, pesos o thresholds sin validación.
- No crear targets ML circulares a partir del propio sistema experto y presentarlos como validación independiente.
- No forzar ML si no existe target o ground truth defendible.
- Mantener GPS como fuente complementaria y opcional.
- No depender de datos del rival para el modo principal.
- No presentar GPS sintético como observación fisiológica real.
- No inventar validaciones con entrenadores, usuarios o clientes.

## Product UX

Principio de diseño:

```text
insight-first, audit-detail second
```

La interfaz debe responder primero qué necesita entender el entrenador y permitir después profundizar en métricas, tablas, dimensiones, provenance y calidad de datos.

El dashboard profesional está operativo. El trabajo de producto pendiente se concentra principalmente en el Data Collector y en el QA final end-to-end.

## Informes PDF

Capa activa:

```text
reports/report_metrics.py
→ report_descriptive_v0.2

reports/data_builder.py
→ schema 0.7.0

reports/pdf_engine_elite_v6.py
→ Team / Player / Match
```

Los informes consumen analytics ya calculados y no implementan una segunda lógica de negocio.

Estado:

```text
REPORTS ELITE TECHNICAL GATE V6: PASS
Team PDF   = 4 páginas
Player PDF = 3 páginas
Match PDF  = 3 páginas
GPS        = integrado y etiquetado
```

La revisión visual final no detectó clipping, solapamientos graves ni tablas fuera de página.

## GPS demo y validación física descriptiva

Demo activa:

```text
generator_version=gps_synthetic_demo_v1.2.0
observations=38197
summary_rows=590
latest_rows=590
```

Validaciones principales:

```text
GPS SYNTHETIC DEMO CONTRACT: PASS
GPS SYNTHETIC COHERENCE AUDIT: PASS
GPS PHYSICAL SUMMARY CONTRACT: PASS
source_precedence_fixture=REAL_OVER_SYNTHETIC:PASS
```

La demo sirve para validar el flujo técnico, no para demostrar fisiología real, fatiga, riesgo de lesión ni calidad del jugador.

## Extensiones futuras

No forman parte del núcleo necesario para cerrar el TFM actual:

- **Power BI** como capa alternativa de consumo sobre el mismo modelo de datos;
- **validación con entrenadores/analistas reales** para medir utilidad percibida y usabilidad;
- **viabilidad comercial / go-to-market** como complemento empresarial;
- **automatización del Data Collector** mediante visión por computador/análisis automático de vídeo;
- **edad, altura y peso** si existe una fuente fiable y una justificación analítica;
- **módulo médico/lesiones** solo con datos reales autorizados, gobernanza específica y sin predicción clínica no validada;
- Rival Mode y análisis de matchups cuando existan datos fiables del rival.

## Product Spiral

La capa de mejora automática del producto está documentada en [`product/README.md`](product/README.md).

Las mutaciones automáticas están limitadas a presentación. Analytics, datos, features, motor experto, LLM, GPS y scores permanecen protegidos. El runner nunca debe hacer push o merge automático y el gate visual humano sigue siendo obligatorio.

## Instalación local

Requiere Python compatible con las dependencias declaradas en `requirements.txt`.

```powershell
git clone <URL_DEL_REPOSITORIO>
cd football-performance-system
python -m pip install -r requirements.txt
```

## Ejecutar la aplicación

```powershell
streamlit run app\streamlit_app.py
```

Por defecto busca:

```text
data/football_performance.duckdb
```

También puede indicarse otra base:

```powershell
$env:FPS_DB_PATH = "C:\ruta\a\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

## Validaciones principales

Según el módulo afectado:

```powershell
python app\validate_dashboard.py
python app\validate_ui_compatibility.py
python app\validate_attention_flags.py
python llm\validate_assistant.py
python llm\validate_stage2.py
python analytics\validate_stage1.py
python gps\validate_synthetic_demo.py --db $env:FPS_DB_PATH
python gps\audit_synthetic_plausibility.py --db $env:FPS_DB_PATH
python gps\validate_physical_summary.py --db $env:FPS_DB_PATH
python reports\validate_reports_pro.py
python publication\validate_public_demo.py
```

Los validadores específicos de Match Rating, Feature Engine, sistema experto y DS/IA se mantienen en sus módulos correspondientes.

## Publicación y datos

Durante desarrollo se han utilizado datos profesionales PannaData/Opta para validación. Esa fuente no define las variables del producto amateur y no se redistribuye automáticamente.

Anonimizar nombres no concede derechos de publicación. Si la licencia no permite redistribución, el repositorio público deberá utilizar un dataset sintético reproducible o un dataset abierto con licencia compatible.

## Estructura del repositorio

```text
football-performance-system/
├── analytics/        # evidencia y analytics estructurados
├── app/              # aplicación Streamlit y access layer
├── collector/        # Data Collector HTML
├── data/             # esquema, importadores y contratos
├── decision_tree/    # sistema experto N1000-N13000
├── docs/             # arquitectura, decisiones y metodología
├── dsai/             # experimentación DS/ML
├── features/         # Feature Engine
├── gps/              # normalización y capa física opcional
├── llm/              # Coach Copilot, tools y guardrails
├── product/          # Product Spiral / QA de presentación
├── publication/      # anonimización y demo pública
├── reports/          # motor PDF
├── tests/            # tests y regresión
├── README.md
└── PROJECT_STATE.md
```

## Prioridad actual

El núcleo analítico no se reconstruye salvo incidencia concreta o evidencia nueva.

Orden de cierre actual:

1. finalizar Data Collector: UX + castellano + mobile-first;
2. QA/regresión global end-to-end;
3. cerrar documentación del TFM: hipótesis, metodología, experimentos, resultados, limitaciones y conclusiones;
4. asegurar instalación/demo reproducible;
5. validar con entrenadores/analistas reales si es viable;
6. preparar defensa y demo final;
7. solo si queda margen, añadir Power BI o una sección comercial como complementos opcionales.

Criterio de cierre:

**producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
