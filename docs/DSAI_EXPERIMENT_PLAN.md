# DSAI experimental plan

Fecha: 26/09/2026

Este documento fija el plan experimental metodológico del TFM. No define por sí solo métricas de producto, recomendaciones tácticas ni umbrales operativos.

## Objetivo principal actualizado

El objetivo central de la fase DS/ML es apoyar la construcción y validación de un **score de rendimiento jugador-partido**.

```text
PLAYER-MATCH DATA
→ PERFORMANCE DIMENSIONS
→ VALIDATED PERFORMANCE SCORE
→ EVOLUTION / CONSISTENCY
→ ROLE CONTEXT
→ COACH INSIGHTS
```

La posición/rol queda como contexto de comparación y normalización, no como target principal.

## Evidencia ya cerrada

### DSAI-02 — Change detection
Resultado: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

### DSAI-03 — Player similarity
Resultado: `EXPLORATORY_RESULT / NO_DEPLOY` por baja estabilidad temporal.

### DSAI-04..08 — Auditoría y reconstrucción del target de rol
Se detectó y corrigió la mezcla de `Substitute` con roles tácticos y se obtuvo una granularidad de fuente de 7 posiciones.

### DSAI-09 — Clasificación post-partido de `source_position`
Resultado:
```text
accuracy=0.5537
balanced_accuracy=0.3482
macro_f1=0.3614
```
Decisión: `EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY`.

### DSAI-10 — Clasificación pre-match de `source_position`
Resultado:
```text
accuracy=0.4834
balanced_accuracy=0.3121
macro_f1=0.3002
```
Decisión: `PREMATCH_EXPERIMENTAL_SIGNAL / NO_DEPLOY`.

### DSAI-11 — Robustez de la línea de posición
Resultado clave:
```text
ML all-safe accuracy=0.4929
last observed position accuracy=0.8944
modal historical position accuracy=0.8915
head-to-head ML only correct=13
last-position only correct=150
```

Decisión: `POSITION_CLASSIFICATION_LINE_CLOSED / CONTEXT_ONLY`.

La posición es muy persistente y una heurística pre-match simple supera ampliamente al ML. No se justifica seguir consumiendo tiempo en optimizar esta tarea. La posición se conserva como variable contextual para analizar rendimiento.

## PERF-01 — Performance score audit — PRIORIDAD ACTUAL

**Pregunta:** ¿qué evidencia y validación necesitamos para construir un score global de rendimiento sin inventar pesos ni convertir volumen en calidad de forma automática?

**Unidad:** `player_id + match_id` con minutos > 0.

**Inputs candidatos:** únicamente variables aprobadas y recollibles de FEATURE-01/Analytics/Expert evidence. GPS solo cuando exista información real.

**Auditoría:**
- cobertura por feature;
- cobertura por dimensiones N4000-N7000;
- disponibilidad de contexto de rol;
- búsqueda de anchors externos de validación en la fuente profesional;
- identificación explícita de métricas con dirección/valor no validado.

**Script:**
```powershell
python dsai\performance_score_audit.py
```

**Guardrails:**
- no producir score en la auditoría;
- no asumir que más volumen implica mejor rendimiento;
- no introducir pesos iguales por defecto;
- no usar el propio sistema experto como ground truth independiente;
- un rating externo, si existe, solo puede ser anchor de validación y nunca input obligatorio del producto amateur.

## Fases siguientes condicionadas a PERF-01

### Ruta A — existe anchor externo defendible
Auditar semántica, cobertura e independencia. Si pasa, estudiar un modelo supervisado que aproxime rendimiento usando únicamente features recollibles. El anchor no se incorpora al producto.

### Ruta B — no existe anchor externo defendible
Validar el constructo mediante:
- literatura;
- criterio experto/entrenador independiente;
- análisis de estabilidad y sensibilidad;
- ablations;
- validación convergente/externa disponible.

No se usarán pesos inventados para acelerar la construcción.

### Dimensiones antes que score global
El score global no se construye directamente. Primero deben quedar defendibles dimensiones separadas de rendimiento basadas en las familias ya existentes (amenaza, creación/progresión, defensa, finalización y, en el futuro, componente físico).

## Líneas bloqueadas

### Role/player fit
Sigue `REFORMULATE_TARGET`. No existe ground truth independiente de fit.

### Expert vs ML
Sigue `BLOCKED_SHARED_TARGET` hasta que ambos métodos puedan resolver la misma tarea contra una referencia independiente común.

### N13000 recommendation calibration
Sigue `BLOCKED_GROUND_TRUTH`.

## GPS

El desarrollo actual tiene `GPS observations=0`. GPS no entra en el score base ni en experimentos que pretendan validar datos inexistentes. La arquitectura de importación queda preparada.

## Criterios comunes de validación

```text
baseline simple primero
→ split temporal cuando proceda
→ cero data leakage
→ target/constructo independiente cuando sea necesario
→ métricas adecuadas
→ cobertura y missingness
→ análisis de error
→ estabilidad / sensibilidad
→ ablations
→ limitaciones explícitas
→ reproducibilidad
```

Un resultado negativo o `NO_DEPLOY` sigue siendo válido académicamente si está bien formulado y documentado.

## Secuencia actual

```text
DSAI-02..11               CERRADOS
        ↓
PERF-01 score audit       ACTIVO
        ↓
validación de dimensiones
        ↓
validación de pesos / target
        ↓
performance score v0.x
        ↓
evolución + contexto de rol
        ↓
Product UX / Reports / Assistant
```
