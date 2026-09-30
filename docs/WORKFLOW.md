# Workflow del proyecto — fases, agentes y gates

Fecha: 30/09/2026

Este documento define cómo se trabaja sobre el estado actual del Football Performance System.

`PROJECT_STATE.md` y el código actual de `main` prevalecen sobre descripciones históricas de fases ya superadas.

## 1. Regla operativa

El proyecto ya no está en fase de construcción del núcleo base. Data, Features, Analytics, sistema experto, experimentación DS/IA baseline y Match Rating están construidos o validados en su estado actual.

La fase activa es **FINAL PRODUCT**: robustez, QA, presentación, Coach Copilot, Reports, Collector UX, demostración GPS, Performance Index y documentación final.

Regla principal:

**No reabrir una capa cerrada salvo incidencia concreta, nueva evidencia o Decision Gate explícito.**

## 2. Estado de fases

```text
F0  ARCHITECTURE                    CERRADO
F1  DATA / COLLECTOR CORE           CERRADO
F2  FEATURES                        CERRADO
F3  ANALYTICS                       CERRADO / VALIDADO
F4  EXPERT / DECISION BASELINE      CERRADO / VALIDADO
F5  DS / AI EXPERIMENTAL CORE       CERRADO EN BASELINE ACTUAL
F6  PRODUCT UX                      IMPLEMENTADO / GATE VISUAL FINAL
F7  REPORTING + ASSISTANT           ACTIVO / QA FINAL
F8  FINAL PRODUCT / PUBLICATION     ACTIVO
```

`PROJECT_STATE.md` mantiene el detalle técnico y las versiones exactas.

## 3. Orden actual de trabajo

```text
DOCUMENTATION SYNC
        ↓
COACH COPILOT QA
        ↓
PRODUCT SPIRAL + DASHBOARD REVIEW
        ↓
HUMAN VISUAL GATE
        ↓
REPORTS-02 VISUAL GATE
        ↓
COLLECTOR UX / ES / MOBILE
        ↓
GPS DEMO
        ↓
PERFORMANCE INDEX / HISTORICAL LAYER
        ↓
GLOBAL QA / REGRESSION
        ↓
TFM DOCUMENTATION / PUBLICATION PACKAGE
```

No volver automáticamente a DATA / FEATURES / EXPERT / MATCH RATING si no existe un fallo concreto o evidencia nueva.

## 4. Agentes / responsabilidades

### A0 — Architect / Integrator

Responsable de:

- mantener arquitectura y contratos;
- inspeccionar el código real antes de proponer cambios;
- coordinar dependencias;
- impedir lógica duplicada;
- detectar documentation drift;
- actualizar `PROJECT_STATE.md` cuando cambia una fase;
- determinar el siguiente bloque real.

Activo durante todo el proyecto.

### A1 — Data & Collector

Propietario de:

- Collector;
- taxonomía de eventos;
- esquema raw/normalized;
- imports;
- GPS normalization;
- data quality.

Estado actual: core cerrado; Collector en mejora de producto.

Pregunta de control: ¿la variable es observable, trazable y realista para fútbol amateur?

### A2 — Feature Engine

Propietario de:

- ratios/per90;
- historial strict-past;
- ventanas/tendencias matemáticas;
- features por rol;
- features físicas validadas.

Estado actual: baseline cerrado.

Pregunta de control: ¿la transformación es reproducible y leakage-safe?

### A3 — Analytics

Propietario de:

- evolución;
- cambio;
- consistencia;
- comparaciones;
- sample sufficiency;
- incertidumbre;
- evidencia estructurada;
- alertas descriptivas.

Estado actual: baseline validado.

Pregunta de control: ¿qué puede afirmar el sistema a partir de evidencia estructurada sin inventar una recomendación?

### A4 — Expert / Decision Engine

Propietario de:

- N1000–N13000;
- reglas;
- confidence;
- justification;
- recommendation gate.

Estado actual: baseline validado y auditable.

Pregunta de control: ¿la decisión es auditable, reproducible y autorizada por una policy validada?

### A5 — ML / Validation

Propietario de:

- experimentación DS/ML;
- similitud/perfiles;
- change detection;
- role-fit cuando exista target válido;
- comparación Expert vs ML cuando sea metodológicamente válida;
- validación fuera de muestra;
- análisis de error;
- ablations;
- reproducibilidad.

Estado actual: baseline experimental documentado. No es la prioridad inmediata de producto salvo que Performance Index o una hipótesis nueva justifiquen reabrir un experimento.

No se fuerza un modelo cuando no existen labels, ground truth o muestra suficiente.

### A6 — Product / UX

Propietario de:

- Home / Command Center;
- Team / Player / Match;
- Physical/GPS;
- jerarquía de información;
- charts;
- navegación;
- responsive;
- estados vacíos;
- detalle/auditoría.

Principio aprobado:

```text
insight-first, audit-detail second
```

Pregunta de control: ¿qué necesita entender primero el entrenador?

### A7 — Reporting

Propietario de:

- Team Report;
- Player Report;
- Match Report;
- composición visual;
- paginación;
- export estático.

Consume resultados ya calculados. No crea nueva lógica analítica.

Estado actual: contracts técnicos pasan; gate visual pendiente.

### A8 — AI Assistant

Propietario de:

- lenguaje natural;
- routing de tools;
- retrieval de contexto estructurado;
- síntesis;
- explicación;
- provider routing;
- guardrails.

Arquitectura actual:

```text
analytics materializados
→ Python tools read-only
→ Ollama local
→ Coach Copilot
```

No calcula conclusiones críticas.

Estado actual: implementado; QA adaptativo final en curso.

### A9 — QA / Publication

Propietario de:

- tests;
- regressions;
- contract gates;
- seguridad;
- privacidad;
- anonimización;
- demo;
- instalación limpia;
- release/documentación.

Acompaña todas las fases.

## 5. Paralelismo permitido

Permitido:

- A0 y A9 acompañan todas las tareas;
- Coach Copilot QA y Product Spiral pueden ejecutarse en paralelo si no comparten mutaciones críticas;
- Product UX y Reports pueden mejorarse en paralelo respetando sus contracts;
- Collector UX puede avanzar sin modificar la semántica de variables;
- documentación final puede prepararse a medida que se cierran bloques.

No permitido:

- Product inventando métricas;
- Reports recalculando analytics;
- LLM accediendo directamente a DuckDB o recalculando scores;
- LLM emitiendo recomendaciones bloqueadas;
- Product Spiral modificando analytics, datos, features, decision engine, LLM o GPS;
- ML definiendo labels por intuición no documentada;
- crear targets ML circulares y presentarlos como validación independiente;
- alterar Match Rating V5 sin evidencia y validación nuevas.

## 6. Product Spiral

La mejora automática de presentación utiliza una allowlist estricta:

```text
app/ui_theme.py
app/coach_ui.py
reports/pdf_engine.py
```

El resto del núcleo analítico está protegido.

Los cambios aceptados quedan en ramas locales `product-spiral-*`; no se hace push ni merge automático.

El score automático solo evalúa cualidades objetivables. El gate visual humano es obligatorio antes de integrar cambios.

## 7. Cómo se cierra un bloque

Cada bloque relevante debe dejar, cuando corresponda:

1. estado inicial / problema;
2. implementación o decisión;
3. validación ejecutada;
4. resultado;
5. limitaciones;
6. regresiones comprobadas;
7. documentación actualizada;
8. siguiente prioridad única.

Una tarea no se considera cerrada únicamente porque compile.

Para UI/PDF debe superar además revisión visual.

Para DS/ML debe existir además:

- hipótesis;
- baseline;
- split/validación apropiada;
- métricas;
- análisis de error;
- decisión de despliegue o no despliegue.

## 8. Decision Gates

Sergi no valida decisiones técnicas ordinarias o reversibles.

Solo se abre un gate si la decisión afecta:

- significado deportivo;
- arquitectura;
- metodología;
- métrica principal;
- política de recomendación;
- UX principal;
- privacidad;
- publicación;
- scope del TFM.

Formato:

```text
ID
DECISIÓN
POR QUÉ IMPORTA
OPCIONES (máximo 2–4)
RECOMENDACIÓN
IMPACTO
DECISIÓN DE SERGI
```

No se abre gate para nombres de funciones, SQL ordinario, caching, tests rutinarios, refactors internos o detalles reversibles.

## 9. Flujo obligatorio de cada sesión/chat

### Al iniciar

1. acceder al repositorio GitHub;
2. leer `PROJECT_STATE.md`;
3. comprobar commits de `main` posteriores a su última actualización;
4. consultar `docs/DECISIONS.md` y documentación específica si la tarea lo requiere;
5. inspeccionar el código real de la funcionalidad afectada;
6. trabajar sobre el estado real, no sobre una conversación antigua.

Orden de precedencia:

```text
código actual + commits recientes
→ PROJECT_STATE.md
→ DECISIONS.md
→ ARCHITECTURE.md
→ documentación del módulo
→ README / WORKFLOW
→ conversaciones antiguas
```

### Durante

- hacer cambios incrementales;
- respetar contracts;
- preferir modificar el módulo existente antes que crear sistemas paralelos;
- validar tras cada cambio relevante;
- no ampliar scope sin justificación.

### Al terminar

1. ejecutar validaciones aplicables;
2. comprobar regresiones;
3. actualizar GitHub/documentación si cambia el estado;
4. indicar a Sergi:
   - qué se completó;
   - qué validó;
   - qué limitación queda;
   - si existe un gate;
   - cuál es el siguiente bloque exacto.

## 10. Prioridad actual aplicada

```text
1  Documentation sync                  ACTIVO
2  Coach Copilot QA                    SIGUIENTE
3  Product Spiral / dashboard review
4  Human visual gate
5  REPORTS-02 visual gate
6  Collector UX / castellano / móvil
7  GPS demo etiquetada
8  Performance Index histórico
9  Global QA / regression
10 TFM docs / publication package
```

El criterio final no es maximizar funcionalidades.

El criterio de cierre es:

**producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
