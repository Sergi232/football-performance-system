# Football Performance System

Sistema de análisis de rendimiento futbolístico orientado a equipos amateur y semiprofesionales sin departamento de análisis propio. Convierte datos sencillos de vídeo y GPS opcional en información estructurada para el cuerpo técnico.

El repositorio forma parte de un Trabajo Final de Máster en **Data Science e Inteligencia Artificial**. El objetivo es doble: construir un producto funcional y reproducible, y demostrar una contribución metodológica sólida en datos, feature engineering, analytics, sistema experto, ML, validación y explicabilidad.

## Estado actual

El prototipo funcional ya contiene:

- Data Collector HTML para captura manual de acciones;
- base de datos DuckDB con unidad principal `jugador-partido`;
- Feature Engine determinista y temporal leakage-safe;
- historial condicionado a rol observado;
- motor experto auditable N1000-N13000;
- dashboard Streamlit con modos Equipo, Jugador, Partidos y Asistente;
- asistente determinista y proveedor OpenAI opcional con guardrails;
- informes PDF de Equipo, Jugador y Partido mediante un motor común;
- normalización GPS multi-proveedor preparada;
- tooling de anonimización para construir una demo pública local;
- capa Analytics en desarrollo para convertir features en evidencia estructurada self/peer.

El estado técnico exacto y el siguiente paso están en [`PROJECT_STATE.md`](PROJECT_STATE.md).

Documentación clave:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura y contratos;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — fases, agentes y gates;
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones estructurales;
- [`docs/DATA_SCIENCE_AI_STRATEGY.md`](docs/DATA_SCIENCE_AI_STRATEGY.md) — estrategia académica Data Science + IA.

## Arquitectura

```text
VÍDEO / DATA COLLECTOR + GPS OPCIONAL
        ↓
BASE DE DATOS
        ↓
FEATURE ENGINE
        ↓
ANALYTICS ENGINE
        ↓
SISTEMA EXPERTO / ML
        ↓
PRODUCT SERVICE LAYER
        ↓
DASHBOARD WEB / INFORMES / ASSISTENT IA
```

La aplicación web es el producto principal. Los PDF son entregables estáticos. El LLM es una capa de interacción y explicación, no el núcleo de cálculo.

## Prioridad Data Science + IA

La cadena metodológica prioritaria del TFM es:

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ ML / EXPERIMENTS
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

El proyecto no se considera completo solo porque exista una interfaz funcional. Antes del cierre debe existir una fase experimental seria de DS/IA con hipótesis, baselines, validación leakage-safe, métricas, análisis de error y una decisión razonada de despliegue o no despliegue.

Casos prioritarios a evaluar:
- player profiles / similarity;
- change detection / evolución;
- role/player fit solo si existe un target defendible;
- comparación Expert vs ML cuando sea metodológicamente válida.

## Principios metodológicos

- Priorizar variables que puedan recogerse de forma realista en un partido de 90 minutos.
- Separar siempre datos brutos, features, analytics, motor de decisión y explicación final.
- Evitar data leakage: las features temporales usan solo información estrictamente anterior.
- No basar conclusiones importantes exclusivamente en un LLM.
- No inventar métricas, scores, rankings, pesos o umbrales sin validación.
- Mantener el GPS como fuente complementaria y opcional.
- No depender de datos del rival para el modo principal.
- Mantener cada decisión del sistema experto como `entrada → condición → resultado → confianza → justificación`.
- No crear targets ML circulares a partir del propio sistema experto y utilizarlos como validación independiente.

## Modos

### Team Mode
Modo principal. Resume equipo, plantilla, partidos, evolución, evidencias de rol y resultados del motor.

### Player Mode
Perfil individual con historial, features temporales, rol observado y evidencia N12000/N13000.

### Match View
Contexto del partido y estadísticas player-match observadas.

### Assistant
Interfaz de lenguaje natural sobre resultados estructurados. Puede utilizar un proveedor generativo opcional, pero no calcula métricas críticas ni puede saltarse los guardrails del motor.

### Rival Mode
Extensión futura. El sistema principal no depende de disponer de datos del rival.

## Motor experto

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
N10000  rol y encaje táctico
N11000  consistencia / tendencia
N12000  player-fit evidence
N13000  recommendation gate
```

El motor final validado es `expert_0.7.0`. N13000 **no emite todavía recomendaciones tácticas** porque la política final de recomendación no está validada con literatura/datos/experimentos. Esta ausencia es deliberada y auditable.

## Informes PDF

El motor actual (`reports/pdf_engine.py`) genera:

- informe de equipo;
- informe de jugador;
- informe de partido.

REPORTS-01 es un prototipo técnico. Los informes finales se rediseñarán después de cerrar Analytics y Product UX para convertirse en entregables profesionales alimentados por los mismos insights estructurados.

## Instalación local

Requiere Python 3.13 o compatible con las dependencias declaradas.

Primera instalación:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd football-performance-system
python -m pip install -r requirements.txt
```

La instalación de dependencias se hace una vez. En ejecuciones posteriores no es necesario repetirla salvo que cambie `requirements.txt`.

## Ejecutar la aplicación

Con una base de datos local compatible:

```powershell
streamlit run app\streamlit_app.py
```

Por defecto la aplicación busca:

```text
data/football_performance.duckdb
```

También puede indicarse otra base:

```powershell
$env:FPS_DB_PATH = "C:\ruta\a\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

## Validaciones principales

```powershell
python app\validate_dashboard.py
python llm\validate_assistant.py
python llm\validate_stage2.py
python reports\validate_reports.py
python analytics\validate_stage1.py
```

Las validaciones del sistema experto y del Feature Engine se mantienen en sus respectivos módulos.

## Demo anonimizada para publicación

Los datos profesionales usados durante desarrollo no se publican directamente.

Para construir y validar una copia local anonimizada:

```powershell
python publication\validate_public_demo.py
```

La demo sustituye nombres e identificadores por aliases `TEAM_001`, `OPP_001`, `PLAYER_001` y `MATCH_001`, conserva la estructura necesaria para probar la aplicación y comprueba que no quedan nombres/identificadores originales en las tablas públicas.

**Importante:** anonimizar técnicamente los datos no concede derechos de redistribución. La base generada queda ignorada por Git y solo podrá publicarse si la licencia de la fuente lo permite. En caso contrario, el repositorio público utilizará un dataset sintético o con licencia compatible. Véase [`publication/README.md`](publication/README.md).

## Datos de desarrollo

Durante desarrollo se han utilizado datos PannaData/Opta para validar una temporada completa con información real. Esa fuente sirve para desarrollo y validación; **no define las variables del producto amateur**.

El sistema deliberadamente limita las variables finales a información que pueda recogerse mediante el Collector y, cuando exista, GPS.

## Estructura del repositorio

```text
football-performance-system/
├── analytics/        # evidencia estructurada self/peer
├── collector/        # Data Collector HTML
├── data/             # esquema, importadores y contratos de datos
├── gps/              # normalización GPS multi-proveedor
├── features/         # Feature Engine
├── decision_tree/    # motor experto N1000-N13000
├── models/           # ML y experimentación posterior
├── llm/              # contexto, guardrails y proveedor LLM opcional
├── app/              # aplicación Streamlit
├── reports/          # motor PDF común
├── publication/      # anonimización y demo pública local
├── tests/            # tests y regresión
├── docs/
├── examples/
├── README.md
└── PROJECT_STATE.md
```

## Seguridad del LLM

Arquitectura obligatoria:

```text
DATA → ANALYTICS → DECISION ENGINE → STRUCTURED CONTEXT → LLM → COACH
```

El LLM puede explicar, resumir y permitir explorar resultados. No puede crear métricas críticas, sobrescribir el motor experto, inventar evidencia ausente ni emitir una recomendación táctica que N13000 no haya autorizado.

La arquitectura final local/cloud/híbrida sigue pendiente de `DG-LLM-01`.

## Próximos bloques

1. cerrar ANALYTICS-01;
2. validar la policy N13000;
3. ejecutar el núcleo experimental Data Science / ML;
4. rediseñar Product UX;
5. convertir Reports/Assistant en capas finales sobre outputs validados;
6. cerrar publicación, GitHub y memoria TFM.
