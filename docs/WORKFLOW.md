# Workflow del proyecto — fases, agentes y gates

Fecha de sincronización: 04/10/2026

Este documento define cómo se trabaja sobre el estado actual del Football Performance System.

`PROJECT_STATE.md` y el código actual de `main` prevalecen sobre descripciones históricas de fases ya superadas.

## 1. Regla operativa

El núcleo funcional está cerrado y el **Global end-to-end QA está en PASS**.

Regla principal:

**No reabrir una capa cerrada salvo incidencia funcional real, nueva evidencia o Decision Gate explícito.**

Un test aislado que falla se interpreta primero dentro de su contrato y del estado documentado; no reabre automáticamente una arquitectura validada.

Para el Coach Copilot queda explícitamente prohibido volver al patrón:

```text
usuario prueba una frase al azar
→ se añade una regla ad hoc
```

Su cobertura se gobierna mediante `COACH_COPILOT_CONTRACT.md` + tests paramétricos + CI + smoke reproducible.

## 2. Estado de fases

```text
F0  ARCHITECTURE                    CERRADO
F1  DATA / COLLECTOR CORE           CERRADO / VALIDADO
F2  FEATURES                        CERRADO / VALIDADO
F3  ANALYTICS                       CERRADO / VALIDADO
F4  EXPERT / DECISION BASELINE      CERRADO / VALIDADO
F5  DS / AI EXPERIMENTAL CORE       CERRADO EN BASELINE ACTUAL
F6  PRODUCT UX                      CERRADO / OPERATIVO
F7  REPORTING + ASSISTANT           CERRADO MVP / VALIDADO
F8  GLOBAL QA                       CERRADO / PASS
F9  FINAL DOCUMENTATION             ACTIVO
F10 REPRODUCIBILITY / CI            PASS / ACTIVO
F11 MEMORIA / DEFENSA               ACTIVO
```

`PROJECT_STATE.md` mantiene versiones, resultados de gates y limitaciones exactas.

## 3. Orden actual de trabajo

```text
FINAL UI CHECK
        ↓
CANONICAL SCREENSHOTS
        ↓
DOCUMENTATION / MANUSCRIPT SYNC
        ↓
SUBMISSION CHECKLIST
        ↓
FORMATTING / DELIVERY
        ↓
DEFENSE / FINAL DEMO
```

No volver automáticamente a DATA / FEATURES / ANALYTICS / EXPERT / MATCH RATING / LLM / REPORTS si no existe un fallo concreto o evidencia nueva.

## 4. Agentes / responsabilidades

### A0 — Architect / Integrator

Responsable de:
- mantener arquitectura y contratos;
- inspeccionar código y `PROJECT_STATE.md` antes de proponer cambios;
- coordinar dependencias;
- impedir lógica duplicada;
- detectar documentation drift;
- decidir cuándo una incidencia requiere reabrir un módulo;
- actualizar estado y siguiente prioridad.

### A1 — Data & Collector

Propietario de Collector, taxonomía, esquema raw/normalized, imports, GPS normalization y data quality.

Estado: **cerrado en el MVP actual**.

Pregunta de control: ¿la variable es observable, trazable y realista para fútbol amateur?

### A2 — Feature Engine

Propietario de ratios/per90, strict-past, tendencia matemática y features por rol.

Estado: **FEATURE-01/02/03 cerrados y validados**.

Pregunta de control: ¿la transformación es reproducible y leakage-safe?

### A3 — Analytics

Propietario de self-history, peer-role, cambio, variabilidad y evidencia estructurada.

Estado: **ANALYTICS-01 cerrado y validado**.

Pregunta de control: ¿qué puede afirmar el sistema sin convertir evidencia descriptiva en una recomendación no validada?

### A4 — Expert / Decision Engine

Propietario de N1000–N13000, reglas, confidence, justification y recommendation gate.

Estado: **expert_0.7.0 cerrado y validado**.

Pregunta de control: ¿la salida es auditable, reproducible y autorizada por una policy validada?

### A5 — DS / ML Validation

Propietario de experimentación, baselines, splits temporales, leakage, análisis de error, ablations y decisión deploy/no-deploy.

Estado: **baseline experimental cerrado**.

Resultados principales:
- change detection: experimental/no deploy;
- similarity: exploratory/no deploy;
- posición/rol: context-only; baseline simple superior al ML.

No se fuerza ML sin target/ground truth defendible.

### A6 — Product / UX

Propietario de Home, Team, Player, Match, Físico/GPS, navegación, charts, responsive y estados vacíos.

Principio:

```text
insight-first, audit-detail second
```

Estado: **operativo y validado contractualmente**.

### A7 — Reporting

Propietario de Team / Player / Match Reports, composición visual y export estático.

Estado: **V6 cerrado; gate técnico + revisión visual PASS**.

Consume resultados calculados; no crea nueva lógica analítica.

### A8 — AI Assistant

Propietario de lenguaje natural, query-space contract, preflight, routing determinista, tools read-only, fallback semántico, grounding, identidad demo y guardrails.

Runtime local:

```text
pregunta
→ preflight / guardrails
→ router determinista de alta confianza
→ Python tools read-only
→ DuckDB / analytics / expert
→ evidencia estructurada
→ respuesta factual
```

Fallback solo cuando persiste ambigüedad dentro del dominio:

```text
pregunta ambigua
→ qwen3.5:4b
→ selección semántica de tool
→ contrato local de tools
→ Python / DuckDB
→ evidencia estructurada
→ respuesta factual
```

Estado local final:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
semantic fallback used=0/28
query-space CI=PASS
```

La media de 0,4 s corresponde a esa batería concreta y no es un SLA universal. El fallback semántico local puede ser sensiblemente más lento en CPU, pero no forma parte de la ruta obligatoria de consultas claras.

Comparaciones por posición:
- GK / CB / FB / DM / CM / AM / W / ST;
- si se pregunta quién ha rendido mejor, se usa Match Rating medio como criterio explícito dentro de la muestra del rol;
- las métricas adicionales son descriptivas;
- no se crea un score nuevo.

Proveedor opcional:

```text
OpenAI API · clave propia
```

Reglas:
- las consultas claras siguen siendo locales/deterministas;
- OpenAI solo puede seleccionar tools FPS bounded/read-only;
- tool calls revalidadas localmente;
- API key del usuario, no persistida en DuckDB ni archivos del proyecto;
- mismo grounding y guardrails;
- contract + CI PASS;
- live API benchmark no validado todavía.

No se implementa `ChatGPT → FPS` mediante MCP en el MVP.

### A9 — QA / Publication

Propietario de tests, regressions, privacidad, anonimización, demo, instalación limpia, release y documentación.

Estado: **Global end-to-end QA PASS / synthetic demo PASS / CI PASS**.

Trabajo activo: cierre visual, capturas y entrega.

## 5. Cómo se interpreta un fallo nuevo

Secuencia obligatoria:

```text
nuevo FAIL
→ consultar PROJECT_STATE + contrato vigente
→ localizar la capa propietaria
→ decidir si es runtime/entorno, validator o producto
→ reproducir el fallo contra el contrato
→ corregir solo si invalida una capacidad aprobada
→ revalidar lo necesario
→ actualizar estado si cambia una decisión o gate
```

No se rediseña arquitectura por defecto.

## 6. Paralelismo permitido

Permitido:
- documentación, capturas y revisión de entrega en paralelo si no modifican contratos analíticos;
- CI después de cambios de documentación/código;
- preparación de memoria y defensa sobre el estado ya validado.

No permitido:
- Product inventando métricas;
- Reports recalculando analytics;
- LLM accediendo directamente a DuckDB o recalculando scores;
- LLM emitiendo recomendaciones bloqueadas;
- ML definiendo labels por intuición no documentada;
- targets ML circulares presentados como validación independiente;
- alterar Match Rating V5 sin evidencia y validación nuevas;
- publicar datos profesionales sin derechos de redistribución.

## 7. Cómo se cierra un bloque

Cada bloque relevante debe dejar:
1. problema/objetivo;
2. implementación o decisión;
3. validación;
4. resultado;
5. limitaciones;
6. regresiones comprobadas;
7. documentación actualizada;
8. siguiente prioridad única.

Para UI/PDF se requiere revisión visual cuando el cambio sea visual.

Para DS/ML se requiere hipótesis, baseline, split/validación, métricas, análisis de error y decisión deploy/no-deploy.

## 8. Decision Gates

Sergi no valida decisiones técnicas ordinarias o reversibles.

Solo se abre un gate si afecta:
- significado deportivo;
- arquitectura;
- metodología;
- métrica principal;
- política de recomendación;
- UX principal;
- privacidad/publicación;
- scope del TFM.

Formato:

```text
ID
DECISIÓN
POR QUÉ IMPORTA
OPCIONES
RECOMENDACIÓN
IMPACTO
DECISIÓN
```

No se abre gate para nombres de funciones, SQL ordinario, caching, tests rutinarios, refactors internos o detalles reversibles.

## 9. Flujo obligatorio de cada sesión/chat

### Al iniciar

1. acceder a GitHub;
2. leer `PROJECT_STATE.md`;
3. comprobar commits de `main` posteriores a su actualización;
4. consultar `docs/DECISIONS.md` y documentación específica si aplica;
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

- cambios incrementales;
- respetar contracts;
- modificar el módulo existente antes que crear sistemas paralelos;
- validar tras cambios relevantes;
- no ampliar scope sin justificación.

### Al terminar

Indicar de forma breve:
- qué se completó;
- qué validó;
- qué limitación queda;
- si existe gate;
- siguiente bloque exacto.

## 10. Prioridad actual

```text
1  Revisión final de documentación/manuscrito
2  Submission checklist
3  Maquetación / entrega
4  Defensa / demo final
```

Criterio de cierre:

**producto funcional + metodología defendible + arquitectura auditable + demostración reproducible + GitHub presentable.**
