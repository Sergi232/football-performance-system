# Estrategia Data Science + IA del TFM

Fecha: 26/09/2026

## 1. Prioridad académica

El TFM pertenece a un máster de Data Science e Inteligencia Artificial. El producto web es el vehículo de entrega, pero el valor académico central debe quedar demostrado en datos, analítica, modelado, validación y explicabilidad.

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ PERFORMANCE SCORE / DS-ML VALIDATION
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

El proyecto no debe convertirse en un dashboard con un LLM añadido.

## 2. Objetivo analítico principal

El objetivo central es construir un **score de rendimiento jugador-partido** útil para el cuerpo técnico y defendible académicamente.

Arquitectura objetivo:

```text
PLAYER-MATCH DATA
→ DIMENSIONES DE RENDIMIENTO
→ SCORE GLOBAL VALIDADO
→ EVOLUCIÓN / CONSISTENCIA
→ CONTEXTO DE ROL
→ INSIGHTS / RECOMENDACIONES
```

Rol y posición son contexto, no el objetivo principal. Pueden usarse para comparar de forma justa, contextualizar métricas o analizar encaje, pero no deben desplazar el foco del rendimiento.

No existe todavía una fórmula de score aprobada. Pesos, signos, escala y thresholds deben validarse.

## 3. Componentes Data Science obligatorios

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
- variables condicionadas a rol cuando proceda;
- futuras features físicas si existe GPS real.

### DS-3 — Analytics estadístico
- comparación jugador vs self-history;
- comparación jugador vs peers del mismo rol cuando exista rol observado;
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

N4000-N7000 ya estructuran dominios de rendimiento, pero su catálogo actual declara explícitamente que higher/lower es descriptivo hasta validar el valor práctico. Por tanto no se pueden sumar directamente en un rating sin validar dirección y peso.

### DS-5 — Performance score
El score debe cumplir:
- unidad principal `player_match`;
- inputs recollibles en fútbol amateur;
- dimensiones separadas antes de agregación global;
- rol como contexto, no como sustituto de rendimiento;
- GPS opcional;
- pesos y signos justificados;
- score reproducible y explicable;
- validación contra referencia independiente cuando sea posible;
- sensibilidad y ablations documentadas.

No se usarán por defecto pesos iguales, PCA interpretado como calidad o una escala 0-100 sin justificación.

## 4. Evidencia DS/ML ya obtenida

### Change detection
Resultado experimental útil pero sin threshold de despliegue.

### Player similarity
Resultado exploratorio con estabilidad temporal insuficiente para producto.

### Observed role classification
Se auditó el target, se separó `Substitute`, se redujo la taxonomía a posiciones de fuente y se ejecutaron modelos leakage-safe hasta DSAI-10.

DSAI-11 queda detenido por reorientación metodológica antes de usarlo como evidencia final. La clasificación de posición estaba ocupando demasiado peso respecto al objetivo principal del TFM.

La posición se conserva como contexto del rendimiento. El trabajo previo sigue siendo útil académicamente como demostración de target audit, leakage control, reformulación de labels y validación temporal.

## 5. PERF-01 — auditoría del score

Antes de calcular un score se audita:
- cobertura real de las FEATURE-01;
- cobertura de dominios N4000-N7000;
- disponibilidad de rol observado;
- posibles anchors externos de validación en la fuente profesional;
- direcciones/pesos todavía no validados.

Un rating externo de proveedor, si existe, solo puede usarse como referencia de validación o target experimental. No puede ser un input obligatorio del producto amateur.

## 6. Role / player fit

No existe todavía un ground truth independiente de fit.

N12000 es evidencia descriptiva y N13000 es un gate. Ninguno puede convertirse en target del ML y luego utilizarse como validación independiente.

Estado: `REFORMULATE_TARGET`.

## 7. Expert vs ML

Solo se puede comparar cuando ambos métodos resuelvan exactamente la misma tarea contra una referencia independiente común.

N13000 no puede actuar simultáneamente como profesor del ML y como verdad de validación.

Estado: `BLOCKED_SHARED_TARGET`.

## 8. Calibración de N13000

La confianza de recomendación necesita outcomes o labels externos defendibles. No se derivará de una regla arbitraria ni del propio score interno.

Estado: `BLOCKED_GROUND_TRUTH`.

## 9. Metodología de validación

Toda experimentación debe respetar:
- splits temporales cuando proceda;
- control explícito de leakage;
- baseline simple antes del modelo complejo;
- target/constructo independiente cuando sea necesario;
- métricas adecuadas;
- análisis de clases, cobertura y missingness;
- ablations;
- análisis de error;
- estabilidad y sensibilidad;
- incertidumbre y límites;
- reproducibilidad.

Cuando no exista muestra, target o criterio suficiente, **no desplegar** es un resultado válido.

## 10. Papel de la IA generativa

El LLM es una capa de interacción y explicación, no el núcleo científico.

```text
DATA → ANALYTICS → DECISION ENGINE → STRUCTURED CONTEXT → LLM → COACH
```

Puede responder preguntas, explicar outputs, resumir evolución y redactar informes. No puede crear el performance score, inventar pesos ni sustituir validación DS/ML.

La arquitectura final local/cloud/híbrida se decide en `DG-LLM-01` más adelante.

## 11. Orden actual

```text
DATA / FEATURES / ANALYTICS ✓
        ↓
EXPERT BASELINE ✓
        ↓
DSAI-02..10 ✓
DSAI-11 ATURADO / CONTEXT ONLY
        ↓
PERF-01 SCORE AUDIT ← ARA
        ↓
DIMENSION VALIDATION
        ↓
WEIGHT / TARGET VALIDATION
        ↓
PERFORMANCE SCORE
        ↓
PRODUCT UX
        ↓
REPORTS + ASSISTANT
        ↓
FINAL PRODUCT / TFM
```

## 12. Criterio académico de éxito

El TFM debe poder defender:
1. cómo se capturan y estructuran los datos;
2. cómo se crean features leakage-safe;
3. qué evidencia estadística se deriva;
4. cómo funciona el sistema experto;
5. cómo se define y valida el constructo de rendimiento;
6. cómo se construye el score sin pesos arbitrarios;
7. qué tareas DS/ML se consideraron, descartaron o reformularon y por qué;
8. cómo se validan estabilidad, error, contexto y evolución;
9. qué aporta la IA generativa y cuáles son sus límites;
10. cómo todo ello llega a un producto usable por el entrenador.
