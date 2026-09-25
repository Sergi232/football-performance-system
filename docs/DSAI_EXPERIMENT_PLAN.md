# DSAI experimental plan

Fecha: 26/09/2026

Este documento congela el plan experimental derivado de `DSAI-01A — feasibility audit`. No define métricas de producto, recomendaciones tácticas ni umbrales operativos. Su función es fijar qué experimentos son metodológicamente defendibles, en qué orden y con qué validación.

## Evidencia disponible

Resultado local de DSAI-01A:

```text
matches=38
players=36
player_match=835
observed-role rows=590
raw observed-role labels=23
labeled_players=28
player-role sequences=87
repeated player-role sequences=67
median repeated sequence length=5
max sequence length=38
FEATURE-01 names=28
FEATURE-01 non-null=6324/23380
analytics rows=46760
GPS observations=0
```

Estados obtenidos:

```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

## Orden experimental congelado

### DSAI-02 — Change detection / evolution — PRIORIDAD 1

**Estado:** GO.

**Pregunta:** ¿podemos detectar cambios relevantes en una serie jugador-rol-métrica sin usar información futura?

**Unidad:** secuencia `player_id + observed primary_role + FEATURE-01 metric` ordenada por `match_date`.

**Baseline:** evidencia temporal strict-past ya validada en FEATURE-03 / Analytics.

**Diseño experimental:**
- usar exclusivamente el historial estrictamente anterior para construir la referencia;
- evaluar estadísticos de desviación respecto al prior sin fijar todavía un umbral de producto;
- validar sensibilidad mediante inyección sintética de cambios en el valor actual, de modo que el baseline strict-past permanezca intacto;
- evaluar varios tamaños de cambio y reportar separación/ROC-AUC experimental, cobertura y casos no evaluables;
- análisis de falsos avisos y de sensibilidad por longitud de historial;
- no desplegar ninguna alerta final hasta validar un criterio operativo.

**Motivo para ir primero:** 67 de 87 secuencias jugador-rol tienen repetición y ya existe infraestructura temporal leakage-safe.

### DSAI-03 — Player similarity / profiles — PRIORIDAD 2

**Estado:** GO EXPLORATORY.

**Pregunta:** ¿podemos representar jugadores por perfiles comparables sin convertir la similitud en una verdad táctica?

**Unidad:** perfil agregado `player + observed role` construido únicamente con FEATURE-01 válidas y partidos con minutos > 0.

**Baseline:** distancia estandarizada / nearest-neighbour simple.

**Validación obligatoria:**
- cobertura de cada feature;
- estandarización calculada dentro del conjunto de referencia apropiado;
- estabilidad ante bootstrap o cambio de ventana temporal;
- sensibilidad a features escasas;
- coherencia descriptiva con rol observado;
- no interpretar proximidad como “mejor jugador” ni como recomendación.

**Limitación principal:** solo 36 jugadores y varios roles con muy pocos jugadores distintos.

### DSAI-04 — Observed-role classification — HOLD / AUDIT DE LABELS

**Estado:** candidato supervisado, no autorizado todavía para entrenamiento final.

Existe `primary_role` observado como label independiente, pero el audit muestra 23 etiquetas con fuerte dispersión y una etiqueta `Substitute` con 172 filas, que no es equivalente a un rol táctico específico.

Antes de entrenar:
1. auditar semántica y procedencia de `primary_role`;
2. separar estado de suplencia de rol táctico cuando la fuente lo permita de forma verificable;
3. no agrupar clases por intuición;
4. volver a medir soporte por clase/jugador;
5. definir split temporal y control de player leakage.

Hasta cerrar este audit, no se usa esta tarea como demostración supervisada principal.

### Role/player fit — REFORMULAR

No existe ground truth independiente de “fit”. N12000 es evidencia descriptiva y N13000 es un gate; ninguno puede convertirse en target ML y después presentarse como validación independiente.

Solo se reabre si aparece un target externo defendible: valoración de entrenador, minutos/selección futura con definición causalmente prudente, etiqueta experta independiente u otro outcome previamente especificado.

### Expert vs ML — BLOQUEADO

La comparación directa necesita una tarea y un ground truth que puedan predecir ambos métodos. No se comparará el ML contra etiquetas creadas por el propio sistema experto.

Puede reabrirse más adelante si una tarea compartida válida emerge del trabajo de DSAI-02/03/04 o de labels externos.

### N13000 recommendation calibration — BLOQUEADO

No hay ground truth de recomendación ni outcome validado para calibrar confianza. El contrato C aprobado sigue siendo el objetivo final, pero N13000 debe mantener `RECOMMENDATION_NOT_ISSUED_*` hasta disponer de criterios y calibración defendibles.

## GPS

El audit devuelve `GPS observations=0`. Por tanto, ningún experimento actual usa GPS. La arquitectura GPS se mantiene preparada, pero no se atribuye valor experimental a datos inexistentes.

## Criterios comunes de validación

Todos los experimentos deberán cumplir:

```text
baseline simple primero
→ split temporal cuando proceda
→ cero data leakage
→ métricas adecuadas a la tarea
→ análisis de cobertura/missingness
→ análisis de error
→ estabilidad / sensibilidad
→ limitaciones explícitas
→ seed y scripts reproducibles cuando aplique
```

Un resultado negativo o `NO DEPLOY` es válido académicamente si el experimento está bien formulado y documentado.

## Secuencia de trabajo

```text
DSAI-01A feasibility audit     CERRADO / PASS
        ↓
DSAI-02 change detection       ACTIVO
        ↓
DSAI-03 similarity/profiles
        ↓
DSAI-04 role-label audit
        ↓
revisión de bloqueados
        ↓
Product UX / Reports / Assistant
```

No se vuelve al pulido del dashboard antes de completar como mínimo DSAI-02 y DSAI-03 con resultados reproducibles.