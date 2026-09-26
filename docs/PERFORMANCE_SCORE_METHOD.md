# Performance score — methodology

Fecha: 26/09/2026

## Objetivo

Construir un score de rendimiento jugador-partido defendible para fútbol amateur/semiprofesional usando datos simples de vídeo y GPS opcional.

El score no nace como una suma directa de estadísticas. La secuencia metodológica es:

```text
RAW / NORMALIZED DATA
→ FEATURE-01
→ PERFORMANCE DIMENSIONS
→ DIRECTION VALIDATION
→ WEIGHT / AGGREGATION VALIDATION
→ PERFORMANCE SCORE
→ TEMPORAL EVOLUTION / CONSISTENCY
→ ROLE CONTEXT
→ COACH INSIGHTS
```

## Estado actual

PERF-01 concluyó `EXPERT_WEIGHT_VALIDATION_REQUIRED`: no existe un rating individual holístico independiente en la fuente profesional auditada que pueda actuar como target supervisado limpio.

Por tanto, el score debe validarse como constructo, no copiar o predecir un rating de proveedor.

## Principios obligatorios

- unidad: `player_id + match_id`;
- solo variables aprobadas y recollibles;
- GPS opcional;
- rol/posición como contexto;
- missing permanece missing;
- no duplicar una misma feature en el agregado final;
- una estadística componente no puede validarse a sí misma como target externo;
- higher/lower no implica better/worse sin validación;
- PCA, correlación o varianza no definen calidad de rendimiento por sí solas;
- ningún peso entra en producto sin análisis de sensibilidad y justificación explícita.

## Dimensiones candidatas existentes

El sistema experto ya contiene evidencia en:
- N4000 — amenaza ofensiva;
- N5000 — creación/progresión;
- N6000 — contribución defensiva;
- N7000 — finalización.

PERF-02 audita si estas familias cubren realmente todas las features aprobadas y detecta métricas no mapeadas, duplicadas o especialmente condicionadas por rol.

## Problemas que PERF-02 debe resolver antes del score

1. **Cobertura** — una dimensión no puede depender de datos que rara vez existen.
2. **Dirección** — una métrica puede ser output, eficiencia, coste, volumen o contexto, pero esa semántica no fija automáticamente el signo.
3. **Redundancia** — una misma feature no puede contarse dos veces silenciosamente.
4. **Rol** — clearances, tackles, crosses o saves dependen fuertemente del rol y del contexto.
5. **Portero** — un score universal no puede ignorar las métricas específicas de portero.
6. **Disciplina** — tarjetas/faltas/penaltis requieren tratamiento explícito, no quedar fuera por omisión.
7. **1v1** — volumen y eficiencia deben distinguirse.

## Ruta prevista después de PERF-02

### PERF-03 — Direction validation
Cada métrica candidata se clasifica como:
- dirección respaldada;
- contexto-dependiente;
- no apta para score global;
- pendiente de evidencia.

La evidencia puede venir de literatura, criterio experto documentado y experimentación reproducible. No se asignará un signo por intuición del LLM.

### PERF-04 — Dimension prototypes
Solo con métricas cuya dirección esté defendida. Se construyen dimensiones separadas antes del score global.

### PERF-05 — Weight and sensitivity study
Se comparan esquemas de agregación defendibles y se cuantifica cuánto cambian rankings/decisiones al variar pesos. Un esquema simple solo puede mantenerse si es robusto y está explícitamente justificado.

### PERF-06 — Performance score experimental
Primera versión del score, todavía sujeta a validación temporal, estabilidad, ablations y contexto de rol.

## Resultado esperado

El producto final debe poder explicar para cada jugador-partido:

```text
score global
+ dimensiones
+ evidencia usada
+ contexto de rol
+ evolución
+ limitaciones / cobertura
```

El LLM únicamente explica estas salidas estructuradas; no recalcula el score.
