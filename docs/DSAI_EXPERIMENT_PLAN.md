# DSAI experimental plan

Fecha: 26/09/2026
Estado: histórico. La fuente de verdad académica actual es `docs/TFM_MANUSCRIPT_DRAFT.md`, `docs/TFM_EVIDENCE_MATRIX.md` y `PROJECT_STATE.md`; este plan conserva decisiones de experimentación y no debe usarse para describir el estado de cierre.

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
Estado: **ATURADO / CONTEXT ONLY**.

La línea se detiene por decisión metodológica: la clasificación de posición estaba desplazando el objetivo principal del TFM. La evidencia DSAI-04..10 se conserva como demostración de target audit, leakage control, reformulación de labels y validación temporal. A partir de aquí la posición solo se usa como contexto del rendimiento.

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

### Primera ejecución y corrección semántica

La primera ejecución produjo:

```text
played_rows=590
players=28
matches=38
features=28
feature_values=6324/16520
role_context=418/590
domain_nodes=24
anchor_columns=home_score,away_score,bigChanceScored
conclusion=SUPERVISED_ANCHOR_CANDIDATE
```

La conclusión de anchor queda **invalidada**: el detector v0.1 trataba coincidencias lexicales amb `score` com si fossin possibles ratings individuals.

- `home_score` i `away_score` són resultat/context del partit;
- `bigChanceScored` és una estadística component de rendiment;
- cap d’aquests tres camps és un anchor holístic independent de rendiment individual.

`performance_score_audit_0.2.0` separa ara coincidència lexical i validesa semàntica. Un `score/index/rank` genèric només pot ser candidat si està explícitament qualificat com a constructe de `player` o `performance`; les coincidències de context i accions components es rebutgen i es documenten.

La reexecució decidirà entre:
- `SUPERVISED_ANCHOR_CANDIDATE`;
- `EXPERT_WEIGHT_VALIDATION_REQUIRED`;
- `INSUFFICIENT_COVERAGE`.

**Guardrails:**
- no produir score en l’auditoria;
- no assumir que més volum implica millor rendiment;
- no introduir pesos iguals per defecte;
- no usar el propi sistema expert com ground truth independent;
- un rating extern, si existeix, només pot ser anchor de validació i mai input obligatori del producte amateur.

## Fases següents condicionades a PERF-01

### Ruta A — existe anchor externo defendible
Auditar semántica, cobertura e independencia. Si passa, estudiar un model supervisat que aproximi rendiment usant només features recollibles. L’anchor no s’incorpora al producte.

### Ruta B — no existe anchor externo defendible
Validar el constructe mitjançant:
- literatura;
- criteri expert/entrenador independent;
- anàlisi d’estabilitat i sensibilitat;
- ablations;
- validació convergent/externa disponible.

No s’utilitzaran pesos inventats per accelerar la construcció.

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

En el experimento que originó este plan no se utilizaban observaciones GPS reales como evidencia para el score. En el cierre del repositorio existe una demo GPS sintética para validar integración, pero sigue habiendo `0` filas de GPS observado no sintético para N9000. GPS no entra en el score base ni en experimentos que pretendan validar fisiología sin datos reales.

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
DSAI-02..10               CERRADOS
DSAI-11                   ATURADO / CONTEXT ONLY
        ↓
PERF-01 score audit       ACTIVO — v0.2 pendiente de reejecución
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
