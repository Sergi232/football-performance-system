# Estrategia Data Science + IA del TFM

Fecha: 26/09/2026

## 1. Prioridad académica

El TFM pertenece a un máster de Data Science e Inteligencia Artificial. El producto web es el vehículo de entrega, pero el valor académico central debe quedar demostrado en datos, analítica, modelado, validación y explicabilidad.

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ DS / ML EXPERIMENTS
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

El proyecto no debe convertirse en un dashboard con un LLM añadido.

## 2. Componentes Data Science obligatorios

### DS-1 — Data engineering y calidad
- esquema reproducible;
- raw vs derived;
- trazabilidad;
- normalización GPS;
- control de missing data;
- tests de contrato.

### DS-2 — Feature engineering
- ratios y tasas reproducibles;
- variables por 90;
- historial temporal strict-past;
- evolución y tendencia;
- variables condicionadas a rol;
- futuras features físicas si existe GPS real.

### DS-3 — Analytics estadístico
- comparación jugador vs self-history;
- comparación jugador vs peers del mismo rol;
- variabilidad;
- cambio temporal;
- tamaño de muestra;
- incertidumbre;
- detección de cambios y señales descriptivas.

No se inventarán umbrales de significancia práctica. Deben justificarse empíricamente o con literatura.

### DS-4 — Sistema experto auditable
El árbol N1000–N13000 actúa como baseline interpretable.

Cada salida importante mantiene:

```text
input
→ condition
→ result
→ confidence/evidence
→ justification
```

El contrato objetivo de N13000 queda aprobado como:

```text
recommendation
+ calibrated confidence
+ evidence
+ auditable justification
+ limitations
+ alternative when appropriate
```

Este contrato no autoriza todavía a emitir recomendaciones. Los criterios de activación, muestra y calibración deben validarse.

## 3. DSAI-01 — fase experimental

Antes de entrenar modelos se ejecuta `DSAI-01A — feasibility audit`.

El audit debe responder para cada caso de uso:
- qué unidad de análisis existe;
- cuánta muestra real hay;
- qué missingness existe;
- si hay secuencia temporal;
- si existe target independiente;
- qué split es defendible;
- qué baseline simple debe preceder al modelo;
- qué métricas usar;
- qué riesgos de leakage/circularidad existen;
- decisión `GO / REFORMULATE / BLOCKED`.

Implementación:

```powershell
python dsai\feasibility_audit.py
```

No entrena modelos ni crea nuevas métricas futbolísticas.

## 4. Casos de uso a evaluar

### 4.1 Player profiles / similarity
Objetivo: construir representaciones comparables condicionadas a rol.

Candidatos:
- escalado robusto;
- distancia entre perfiles;
- nearest neighbours;
- clustering exploratorio si la muestra lo sostiene.

Validación:
- estabilidad por resampling/ventanas;
- coherencia con rol observado;
- evitar interpretar un cluster como verdad táctica.

### 4.2 Change detection / evolución
Objetivo: detectar cambios respecto al historial strict-past.

Baselines existentes:
- delta vs prior mean;
- slope temporal;
- variabilidad previa.

Métodos posteriores posibles:
- control estadístico;
- change-point detection;
- anomaly detection temporal.

Sin labels reales de change point, la evaluación deberá usar robustez temporal, análisis de falsas alertas y perturbaciones sintéticas controladas.

### 4.3 Observed role classification
Es una posible tarea supervisada porque `primary_role` es un label observado, no producido por el sistema experto.

Objetivo académico: comprobar cuánto del rol observado puede recuperarse desde features de rendimiento, no sustituir la fuente de rol.

Antes de entrenar:
- auditar las 23 etiquetas existentes;
- revisar sparsity/imbalance;
- decidir si el label space original es defendible o requiere reformulación aprobada;
- evitar leakage por jugador y tiempo;
- baseline simple primero.

### 4.4 Role / player fit
No existe todavía un ground truth independiente de fit.

N12000 es evidencia descriptiva y N13000 es un gate. Ninguno puede convertirse en target del ML y luego utilizarse como validación independiente.

Estado inicial: `REFORMULATE_TARGET`.

### 4.5 Expert vs ML
Solo se puede comparar cuando ambos métodos resuelvan exactamente la misma tarea contra una referencia independiente común.

N13000 no puede actuar simultáneamente como profesor del ML y como verdad de validación.

Estado inicial: `BLOCKED_SHARED_TARGET` hasta formular la tarea correcta.

### 4.6 Calibración de N13000
La confianza de recomendación necesita outcomes o labels externos defendibles. No se derivará de una regla arbitraria ni del propio score interno.

Estado inicial: `BLOCKED_GROUND_TRUTH`.

## 5. Metodología de validación

Toda experimentación debe respetar:
- splits temporales cuando proceda;
- control explícito de leakage por jugador;
- baseline simple antes del modelo complejo;
- métricas adecuadas a la tarea;
- análisis de clases y missingness;
- ablations cuando aporten información;
- análisis de error;
- incertidumbre y límites;
- reproducibilidad mediante scripts/seeds cuando corresponda.

Cuando no exista muestra o target suficiente, **no desplegar** es un resultado válido si la justificación queda documentada.

## 6. Papel de la IA generativa

El LLM es una capa de interacción y explicación, no el núcleo científico.

```text
DATA → ANALYTICS → DECISION ENGINE → STRUCTURED CONTEXT → LLM → COACH
```

Puede responder preguntas, explicar outputs, resumir evolución y redactar informes. No puede crear métricas críticas, sustituir validación DS/ML ni saltarse N13000.

La arquitectura final local/cloud/híbrida se decide en `DG-LLM-01` más adelante.

## 7. Orden actual

```text
ANALYTICS-01 ✓
      ↓
N13000 POLICY CONTRACT ✓
      ↓
DSAI-01A FEASIBILITY AUDIT ← ARA
      ↓
PLAN EXPERIMENTAL CONGELADO
      ↓
EXPERIMENTOS DS/ML
      ↓
PRODUCT UX
      ↓
REPORTS + ASSISTANT
      ↓
FINAL PRODUCT / TFM
```

## 8. Criterio académico de éxito

El TFM debe poder defender:
1. cómo se capturan y estructuran los datos;
2. cómo se crean features leakage-safe;
3. qué evidencia estadística se deriva;
4. cómo funciona el sistema experto;
5. qué tareas DS/ML se consideraron y por qué;
6. cuáles se descartaron o reformularon y por qué;
7. cómo se validaron los modelos finalmente ejecutados;
8. qué aporta la IA generativa y cuáles son sus límites;
9. cómo todo ello llega a un producto usable por el entrenador.
