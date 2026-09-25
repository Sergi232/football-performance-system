# Workflow del proyecto — fases, agentes y gates

Fecha: 25/09/2026

Este documento define cómo se trabaja a partir de ARCHITECTURE-01.

## 1. Regla operativa

El proyecto avanza por fases ordenadas. Cada fase tiene un agente propietario, entradas, entregables, validación y una condición de salida.

No se implementan interfaces definitivas antes de que las capas analíticas que las alimentan estén cerradas.

## 2. Orden de trabajo

```text
F0  ARCHITECTURE
      ↓
F1  DATA / COLLECTOR       [base casi cerrada]
      ↓
F2  FEATURES               [base cerrada]
      ↓
F3  ANALYTICS              [siguiente trabajo principal]
      ↓
F4  DECISION POLICY        [N13000]
      ↓
F5  PRODUCT UX
      ↓
F6  REPORTING + ASSISTANT
      ↓
F7  ML / VALIDATION AVANZADA si procede
      ↓
F8  FINAL PRODUCT / PUBLICATION / TFM
```

## 3. Agentes

### A0 — Architect / Integrator

Responsable de:
- mantener arquitectura y contratos;
- decidir detalles técnicos no críticos;
- coordinar dependencias;
- impedir lógica duplicada;
- actualizar `PROJECT_STATE.md`;
- decidir qué agente trabaja después.

Activo durante todo el proyecto.

### A1 — Data & Collector

Propietario de:
- Collector;
- taxonomía de eventos;
- esquema raw/normalized;
- imports;
- GPS normalization;
- data quality.

Pregunta de control: ¿la variable es recogible y trazable?

### A2 — Feature Engine

Propietario de:
- ratios/per90;
- historial strict-past;
- ventanas/tendencias matemáticas;
- features por rol;
- futuras features GPS.

Pregunta de control: ¿la transformación es reproducible y leakage-safe?

### A3 — Analytics

Propietario de:
- evolución;
- cambio;
- consistencia;
- comparaciones;
- sample sufficiency;
- incertidumbre;
- alertas descriptivas;
- priorización de insights.

Pregunta de control: ¿qué evidencia estructurada puede afirmar el sistema antes de recomendar?

### A4 — Expert / Decision Engine

Propietario de:
- N1000–N13000;
- reglas;
- policy;
- confidence;
- justification;
- recommendation gate.

Pregunta de control: ¿la decisión es auditable y está validada?

### A5 — ML / Validation

Propietario de:
- similitud;
- clustering/perfiles;
- change detection;
- role-fit ML;
- comparación Expert vs ML;
- validación fuera de muestra.

Solo se activa cuando la hipótesis y los datos lo justifican.

### A6 — Product / UX

Propietario de:
- jerarquía de información;
- TEAM / PLAYER / MATCH;
- charts;
- alertas;
- navegación;
- detalle/auditoría.

Pregunta de control: ¿qué necesita saber primero el entrenador?

### A7 — Reporting

Propietario de:
- Team report;
- Player report;
- Match report;
- composición visual;
- export estático.

Consume Product Service Layer; no crea nueva lógica analítica.

### A8 — AI Assistant

Propietario de:
- lenguaje natural;
- retrieval de contexto estructurado;
- explicación;
- resumen;
- provider routing;
- guardrails.

No calcula conclusiones críticas.

### A9 — QA / Publication

Propietario de:
- tests;
- regresión;
- seguridad;
- privacidad;
- anonimización;
- demo;
- instalación;
- documentación/release.

## 4. Paralelismo permitido

No todos los agentes trabajan secuencialmente.

Permitido:
- A9 QA acompaña todas las fases;
- A0 Architect acompaña todas las fases;
- A6 Product puede diseñar wireframes una vez conocido el output contract de Analytics, aunque A4 siga validando policy;
- A7 Reporting y A8 Assistant pueden avanzar en paralelo después de cerrar Product Service Layer;
- A5 ML puede investigar en paralelo, pero no puede sustituir una policy no validada.

No permitido:
- Product inventando métricas;
- Reports recalculando analytics;
- LLM emitiendo recomendaciones bloqueadas;
- ML definiendo labels a partir de intuición no documentada.

## 5. Cómo pasa una fase a la siguiente

Cada fase debe dejar este paquete:

1. **Input contract** — qué recibe y de dónde;
2. **Definitions** — conceptos cerrados;
3. **Implementation** — código/artefactos;
4. **Validation** — tests o experimento;
5. **Output contract** — qué entrega a la siguiente capa;
6. **Limitations** — qué no puede afirmar;
7. **PROJECT_STATE update**;
8. **Next phase** — una única siguiente prioridad.

Una fase está cerrada solo cuando su salida puede ser consumida sin reinterpretarla.

## 6. Cuándo interviene Sergi

Sergi no debe validar cada decisión técnica.

Interviene solo en un **Decision Gate** cuando exista impacto estructural o de producto.

El agente Architect debe presentar el gate así:

```text
ID
DECISIÓN
POR QUÉ IMPORTA
OPCIONES (máximo 2–4)
RECOMENDACIÓN
IMPACTO DE CADA OPCIÓN
DECISIÓN DE SERGI
```

No se abre gate para:
- nombres de funciones;
- estructura interna de clases;
- SQL ordinario;
- caching;
- tests rutinarios;
- refactors sin impacto de producto;
- detalles reversibles.

## 7. Flujo práctico de cada sesión/chat

Al iniciar:
1. leer `PROJECT_STATE.md`;
2. leer la fase activa en `docs/WORKFLOW.md`;
3. consultar `docs/DECISIONS.md` si hay un gate abierto;
4. trabajar solo en la fase activa o en tareas paralelas permitidas;
5. no reabrir decisiones cerradas sin evidencia nueva.

Al terminar:
1. validar;
2. actualizar GitHub;
3. indicar a Sergi solo:
   - qué se ha completado;
   - si existe un gate que requiera decisión;
   - qué debe probar o decidir;
   - cuál es el siguiente bloque.

## 8. Estado actual aplicado al workflow

```text
A1 Data/Collector       base funcional cerrada
A2 Features             base funcional cerrada
A3 Analytics            INCOMPLETO / siguiente foco
A4 Expert               baseline N1000-N13000 creado; policy final pendiente
A6 Product              prototype v0.1, no final
A7 Reporting            prototype v0.1, no final
A8 Assistant            prototype v0.1, provider final pendiente
A9 Publication tooling  validado técnicamente
```

Por tanto el siguiente trabajo de construcción, después de cerrar ARCHITECTURE-01, es **ANALYTICS-01**.
