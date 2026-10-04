# Estrategia Data Science + IA del TFM

Fecha de sincronización: 04/10/2026

## 1. Prioridad académica

El TFM pertenece a un máster de Data Science e Inteligencia Artificial. El producto web es el vehículo de entrega, pero el valor académico central se demuestra en datos, feature engineering, analítica, modelado, validación, explicabilidad y decisiones de no-deploy cuando la evidencia no es suficiente.

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ MATCH RATING / PERFORMANCE INDEX
→ DS-ML EXPERIMENTATION
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

El proyecto no debe convertirse en un dashboard con un LLM añadido.

## 2. Constructos de rendimiento vigentes

El proyecto distingue dos capas:

```text
MATCH RATING
= evaluación inmediata jugador-partido
= match_rating_v0.5-candidate
= disponible desde partido 1

PERFORMANCE INDEX
= capa histórica/posicional complementaria
= performance_score_v0.2-experimental
```

Match Rating V5 es el baseline activo y validado. El Performance Index sigue siendo experimental y no sustituye al Match Rating.

No se modifican pesos, signos, escalas o arquitectura de Match Rating V5 sin nueva evidencia, experimento explícito y validación.

## 3. Componentes Data Science

### DS-1 — Data engineering y calidad

Cerrado/validado en el MVP actual:
- esquema reproducible;
- raw vs derived;
- trazabilidad;
- normalización GPS;
- control de missing data;
- tests de contrato.

### DS-2 — Feature engineering

Cerrado/validado:
- FEATURE-01: features base;
- FEATURE-02: históricos strict-past;
- FEATURE-03: contexto de rol observado.

Principios:
- ratios/tasas reproducibles;
- per90;
- ausencia preservada;
- temporal leakage control;
- rol observado, no inferido cuando falta evidencia.

### DS-3 — Analytics estadístico

ANALYTICS-01 cerrado/validado.

Incluye:
- comparación jugador vs self-history;
- comparación jugador vs peers del mismo rol observado;
- variabilidad;
- cambio temporal;
- tamaño de muestra/evidencia;
- provenance.

Self-role y peer-role permanecen separados.

No se inventan umbrales de significancia práctica o etiquetas bueno/malo sin justificación.

### DS-4 — Sistema experto auditable

El árbol N1000–N13000 actúa como baseline interpretable.

Cada salida mantiene:

```text
input
→ condition
→ result
→ confidence/evidence
→ justification
```

Estado: `expert_0.7.0` cerrado y validado.

N13000 es un recommendation gate: no emite recomendación táctica sin policy validada.

### DS-5 — Match Rating

Unidad: `player_match`.

Requisitos cerrados:
- disponible desde primer partido;
- 590/590 apariciones jugadas valoradas en la temporada demo;
- modelo posicional de campo cuando existe rol fiable;
- ruta separada de portero;
- fallback genérico cuando el rol no es fiable;
- no inventar posición;
- confidence/provenance;
- no depender de GPS;
- no depender de historia previa del club.

Versión activa: `match_rating_v0.5-candidate`.

### DS-6 — Performance Index

Capa histórica/posicional complementaria.

Versión actual: `performance_score_v0.2-experimental`.

Puede apoyar lectura de evolución, forma, consistencia y contexto de rol, pero su estado experimental debe permanecer explícito.

## 4. Evidencia DS/ML obtenida

### Change detection

Resultado: señal experimental útil, sin threshold de despliegue defendible.

Decisión: `NO_DEPLOY`.

### Player similarity

Resultado: exploratorio, con estabilidad temporal insuficiente.

Decisión: `NO_DEPLOY`.

### Observed/source position classification

Se auditó el target, se separó `Substitute`, se reconstruyó una taxonomía de posición de fuente y se ejecutaron modelos leakage-safe.

El experimento final demostró que un baseline futbolístico simple basado en la última posición observada del jugador (~89.4% accuracy en el benchmark de robustez documentado) superaba claramente al enfoque ML pre-match.

Decisión metodológica:

```text
POSITION / ROLE ML = CONTEXT ONLY / NO DEPLOY
```

Resultado académico relevante: no se fuerza ML cuando una regla simple y trazable funciona mejor.

## 5. Role / player fit

No existe ground truth independiente suficiente de fit.

N12000 es evidencia descriptiva y N13000 es un gate. Ninguno puede convertirse simultáneamente en target ML y referencia independiente de validación.

Estado:

```text
REFORMULATE_TARGET / NO DEPLOY
```

## 6. Expert vs ML

Solo es válido comparar ambos cuando resuelven exactamente la misma tarea contra una referencia independiente común.

N13000 no puede actuar a la vez como profesor del ML y verdad de validación.

Estado:

```text
BLOCKED_SHARED_TARGET
```

## 7. Calibración de recomendación

La confianza/recomendación final requeriría outcomes o labels externos defendibles.

No se deriva de una regla arbitraria ni del propio score interno.

Estado:

```text
BLOCKED_GROUND_TRUTH
```

## 8. GPS

GPS es opcional y descriptivo.

La demo sintética sirve para validar el flujo técnico, no fisiología real.

No se despliegan métricas de HSR, sprint, workload, fatiga, readiness o riesgo de lesión sin definición y validación específica.

GPS sintético no alimenta Match Rating, Performance Index ni decisiones expertas.

## 9. Metodología de validación

Toda experimentación debe respetar:
- splits temporales cuando proceda;
- control explícito de leakage;
- baseline simple antes del modelo complejo;
- target/constructo independiente cuando sea necesario;
- métricas adecuadas;
- análisis de clases, cobertura y missingness;
- ablations;
- análisis de error;
- estabilidad y sensibilidad;
- incertidumbre y límites;
- reproducibilidad.

Cuando no exista muestra, target o criterio suficiente, **no desplegar** es un resultado válido.

## 10. Papel de la IA generativa

La IA generativa es una capa de interacción e interpretación, no el núcleo científico.

Runtime local final:

```text
DATA / ANALYTICS / DECISION ENGINE
→ PREFLIGHT / GUARDRAILS
→ DETERMINISTIC QUERY ROUTER
→ READ-ONLY TOOLS
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ COACH
```

Solo si una consulta no se puede resolver con suficiente confianza y sigue dentro del dominio:

```text
QUESTION AMBIGUA
→ qwen3.5:4b
→ TOOL SELECTION
→ LOCAL TOOL VALIDATION
→ PYTHON / DUCKDB
→ STRUCTURED EVIDENCE
→ COACH
```

Principios:
- MVP en castellano;
- consultas claras sin dependencia de LLM;
- `qwen3.5:4b` únicamente como fallback semántico local;
- ruido, meta-consultas y fuera de dominio obvio se resuelven mediante preflight determinista;
- tools Python read-only;
- sin acceso directo del LLM a DuckDB;
- el LLM no crea Match Rating, Performance Index, features críticas ni decisiones expertas;
- guardrails deterministas para inferencias no validadas;
- follow-ups anclados a la última consulta sustantiva;
- comparación por posición permitida con criterio explícito y sin crear un score nuevo.

Validación local real final:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
all final smoke cases: rounds=0
```

El smoke final cubre rankings, ventanas, perfiles, GPS, comparaciones entre jugadores, comparaciones por posición, partidos, calidad, guardrails, ruido/fuera de dominio y follow-ups.

La aplicación incorpora además un proveedor opcional `OpenAI API · clave propia`. Este modo reutiliza la misma capa de tools y no modifica Analytics/Decision Engine. Las tool calls externas se revalidan localmente y la API key del usuario no se persiste en DuckDB ni archivos del proyecto. La integración pasa contract tests y CI, pero no dispone todavía de benchmark live con una API key real.

La decisión metodológica importante es que el valor de IA no se mide por cuántas consultas pasan por un LLM, sino por si la interfaz mejora la accesibilidad sin comprometer grounding, trazabilidad y límites de inferencia.

## 11. Orden académico actual

```text
DATA / FEATURES / ANALYTICS          ✓
EXPERT BASELINE                     ✓
MATCH RATING V5                     ✓
PERFORMANCE INDEX EXPERIMENTAL      ✓
DS/ML EXPERIMENTS + NO-DEPLOY       ✓
COACH COPILOT FINAL 28/28           ✓
OPENAI BYOK CONTRACT                ✓
REPORTS / PRODUCT                   ✓
GLOBAL END-TO-END QA                ✓
DOCUMENTATION SYNC                  ✓
        ↓
CAPTURAS / MAQUETACIÓN              ← ACTUAL
        ↓
ENTREGA
        ↓
DEFENSA / DEMO
```
