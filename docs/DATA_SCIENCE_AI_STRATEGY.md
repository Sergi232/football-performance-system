# Estrategia Data Science + IA del TFM

Fecha: 25/09/2026

## 1. Prioridad académica

El TFM pertenece a un máster de Data Science e Inteligencia Artificial. Por tanto, el producto web es el vehículo de entrega, pero el valor académico central debe quedar demostrado en las capas de datos, analítica, modelado, validación y explicabilidad.

El proyecto no debe convertirse en un dashboard con un LLM añadido. La cadena metodológica prioritaria es:

```text
DATA
→ FEATURE ENGINE
→ ANALYTICS / STATISTICS
→ EXPERT SYSTEM
→ ML / EXPERIMENTS
→ VALIDATION / EXPLAINABILITY
→ PRODUCT
→ LLM
```

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

Cada salida importante debe mantener:

```text
input
→ condition
→ result
→ confidence/evidence
→ justification
```

El sistema experto no se considera sustituto del ML: sirve como baseline y como referencia explicable.

## 3. Componentes ML / IA a evaluar

El proyecto debe incluir una fase experimental de ML antes del cierre final. No todos los modelos tienen que llegar a producción; sí deben formularse hipótesis, validarse y compararse correctamente.

Prioridad de casos de uso:

1. **Player profiles / similarity**
   - clustering o representación vectorial;
   - similitud entre jugadores condicionada a rol;
   - validación de estabilidad y utilidad.

2. **Change detection / evolución**
   - detección estadística o ML de cambios de rendimiento;
   - comparación contra reglas descriptivas simples.

3. **Role / player fit**
   - solo si existen labels o una definición de objetivo defendible;
   - evitar crear targets circulares a partir del propio sistema experto.

4. **Expert vs ML**
   - comparar al menos un caso donde ambos enfoques puedan resolver la misma tarea;
   - métricas, validación temporal y análisis de errores.

## 4. Metodología de validación

Toda experimentación debe respetar:

- splits temporales cuando proceda;
- cero data leakage;
- baseline simple antes del modelo complejo;
- métricas adecuadas a la tarea;
- ablation / comparación de features cuando aporte información;
- análisis de error;
- incertidumbre y límites;
- reproducibilidad mediante scripts y seeds cuando corresponda.

Cuando no exista muestra suficiente, el resultado válido puede ser **no desplegar el modelo**, siempre que el experimento y la justificación queden documentados.

## 5. Papel de la IA generativa

El LLM es una capa de interacción y explicación, no el núcleo científico.

Arquitectura:

```text
DATA → ANALYTICS → DECISION ENGINE → STRUCTURED CONTEXT → LLM → COACH
```

La IA generativa puede:
- responder preguntas en lenguaje natural;
- explicar outputs calculados;
- resumir evolución y evidencia;
- redactar informes a partir de contexto estructurado.

No puede:
- inventar métricas;
- recalcular resultados críticos;
- crear rankings no autorizados;
- sustituir la validación estadística/ML;
- emitir una recomendación que N13000 no permita.

La arquitectura final del provider (local/cloud/híbrida) se decide en `DG-LLM-01`.

## 6. Nueva prioridad de trabajo

Después de cerrar ANALYTICS-01:

```text
ANALYTICS-01
      ↓
N13000 POLICY
      ↓
DS/AI EXPERIMENTAL CORE
  ├─ statistical validation
  ├─ player similarity / profiles
  ├─ change detection
  └─ expert vs ML cuando sea metodológicamente válido
      ↓
PRODUCT UX
      ↓
REPORTS + ASSISTANT
      ↓
FINAL PRODUCT / TFM
```

El rediseño visual no debe absorber tiempo que corresponda a la parte científica.

## 7. Criterio académico de éxito

El TFM debe poder defender claramente:

1. cómo se capturan y estructuran los datos;
2. cómo se crean features leakage-safe;
3. qué evidencia estadística se deriva;
4. cómo funciona el sistema experto;
5. qué tareas se probaron con ML y por qué;
6. cómo se validaron y compararon;
7. qué aporta la IA generativa y qué límites tiene;
8. cómo todo ello se transforma en un producto usable por un entrenador.

El producto es importante, pero la contribución Data Science + IA debe ser visible, evaluable y reproducible por separado de la interfaz.
