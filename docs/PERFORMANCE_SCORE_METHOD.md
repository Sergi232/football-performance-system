# Performance score — methodology

Fecha: 26/09/2026

## Objetivo

Construir un score de rendimiento jugador-partido defendible para fútbol amateur/semiprofesional usando datos simples de vídeo y GPS opcional.

El score no nace como una suma directa de estadísticas. La secuencia metodológica actual es:

```text
RAW / NORMALIZED DATA
→ FEATURE-01
→ PERFORMANCE DIMENSIONS
→ DIRECTION VALIDATION
→ SIGNED CORE FEASIBILITY
→ GOALKEEPER-SPECIFIC VALIDATION
→ NORMALIZATION / AGGREGATION FEASIBILITY
→ EXPERIMENTAL PERFORMANCE SCORE
→ SENSITIVITY / ABLATIONS
→ VALIDATED PERFORMANCE SCORE
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

Esto significa que 11 FEATURE-01 tienen una dirección defendible y 17 deben conservarse como contexto en lugar de forzarse dentro de un score.

PERF-05 confirmó que todas las dimensiones outfield tienen al menos una feature signada.

PERF-06 y PERF-07 validaron para portero:

```text
save_rate = saves / (saves + goals_conceded)
```

con 31 player-match derivables, todos `Goalkeeper`, sin conflictos de rol y sin `saves > 0` asignados a roles actuales no-portero. `save_rate` queda admitida como feature role-specific para la línea del score, con limitación explícita: no ajusta calidad del tiro porque no existe xGOT/PSxG en la fuente.

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
- `CONTEXT_DEPENDENT` no equivale a cero valor: significa que la métrica no puede recibir un signo universal sin contexto adicional;
- `save_rate` es específica de portero y no se aplica a jugadores de campo;
- no se inventan xGOT/PSxG, calidad de tiro ni datos del rival.

## Dimensiones estructurales actuales

- `attacking_threat`;
- `creation_progression`;
- `defensive_contribution`;
- `finishing`;
- `discipline`;
- `goalkeeping` (role-specific).

Cada FEATURE-01 tiene exactamente una dimensión primaria. `shots_total_per90` conserva finalización como contexto secundario pero no puede contarse dos veces en un agregado.

## Núcleo firmado

Jugador de campo: 11 FEATURE-01 con dirección respaldada repartidas por las cinco dimensiones outfield.

Portero: `save_rate` se añade como evidencia role-specific validada para la dimensión `goalkeeping`; todavía no se mezcla con el score outfield.

## PERF-08 — Normalización y agregación

Antes de crear el primer score se audita:
- cobertura y missingness;
- dispersión y zero-inflation;
- si las features tienen soporte suficiente para normalización robusta/rank-based;
- cobertura de dimensiones;
- soporte de contexto por posición cuando esté disponible;
- separación outfield / goalkeeper.

No se crea todavía un score ni se aprueban pesos.

## Baseline experimental previsto

Si PERF-08 pasa, el primer score será deliberadamente simple y auditable:
1. aplicar la dirección validada a cada feature;
2. normalizar con el método más robusto frente a asimetría/ties que soporte la evidencia;
3. agregar feature → dimensión;
4. agregar dimensión → global para que una dimensión no pese más solo por tener más features;
5. usar pesos iguales únicamente como **baseline nulo experimental**;
6. comparar sensibilidades, ablations y estabilidad antes de aprobar cualquier esquema.

Equal weighting no se considera verdad experta ni peso final: es el punto de referencia contra el que se probarán alternativas.

## Resultado esperado

El producto final debe poder explicar para cada jugador-partido:

```text
score global
+ dimensiones
+ evidencia usada
+ cobertura
+ contexto de rol
+ evolución
+ limitaciones
```

El LLM únicamente explica estas salidas estructuradas; no recalcula el score.
