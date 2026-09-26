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
→ SIGNED CORE FEASIBILITY
→ WEIGHT / AGGREGATION VALIDATION
→ PERFORMANCE SCORE
→ TEMPORAL EVOLUTION / CONSISTENCY
→ ROLE CONTEXT
→ COACH INSIGHTS
```

## Estado actual

PERF-01 concluyó `EXPERT_WEIGHT_VALIDATION_REQUIRED`: no existe un rating individual holístico independiente en la fuente profesional auditada que pueda actuar como target supervisado limpio.

PERF-03 cerró el mapping estructural de 28/28 FEATURE-01 en seis dimensiones primarias sin duplicación primaria.

PERF-04 cerró la clasificación de direcciones:

```text
POSITIVE_SUPPORTED = 6
NEGATIVE_SUPPORTED = 5
CONTEXT_DEPENDENT = 17
PENDING_EVIDENCE = 0
```

Esto significa que 11 features tienen una dirección defendible y 17 deben conservarse como contexto en lugar de forzarse dentro de un score.

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
- ningún peso entra en producto sin análisis de sensibilidad y justificación explícita;
- `CONTEXT_DEPENDENT` no equivale a cero valor: significa que la métrica no puede recibir un signo universal sin contexto adicional.

## Dimensiones estructurales actuales

- `attacking_threat`;
- `creation_progression`;
- `defensive_contribution`;
- `finishing`;
- `discipline`;
- `goalkeeping` (role-specific).

Cada FEATURE-01 tiene exactamente una dimensión primaria. `shots_total_per90` conserva finalización como contexto secundario pero no puede contarse dos veces en un agregado.

## PERF-05 — Signed core feasibility

Antes de crear dimensiones puntuables se audita el núcleo de features con dirección respaldada.

Se comprobará:
- cobertura real de las 11 features firmadas;
- cobertura por dimensión;
- dimensiones sin ninguna feature firmada;
- diferencias estructurales entre jugadores de campo y porteros;
- filas con evidencia suficiente por dimensión, sin agregación.

No se crearán medias, z-scores, pesos, percentiles, rankings ni score.

Si una dimensión depende solo de métricas `CONTEXT_DEPENDENT`, no se forzará una dirección para completar artificialmente el score.

## Ruta posterior prevista

### PERF-06 — Dimension prototypes
Solo después de PERF-05. Se podrán comparar prototipos de agregación explícitos como experimentos, nunca como fórmula aprobada por defecto.

### PERF-07 — Weight and sensitivity study
Comparar esquemas de agregación defendibles y cuantificar cuánto cambian resultados al variar pesos. Un esquema simple solo puede mantenerse si es robusto y está explícitamente justificado.

### PERF-08 — Performance score experimental
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
