# Coach Copilot — Self-Improve QA

Estado: **herramienta experimental de QA local; no forma parte del gate obligatorio de entrega**.

## Objetivo

Mejorar la robustez lingüística del Coach Copilot sobre casos de uso reales de entrenador sin permitir que el proceso modifique automáticamente analytics, Match Rating, Performance Index, sistema experto, reglas de decisión ni pesos del modelo.

No es fine-tuning. La mejora automática se limita a:

- selección adaptativa de casos débiles;
- replay de fallos;
- variaciones lingüísticas ES/CA que preservan la intención;
- búsqueda controlada del mejor perfil de síntesis Ollama;
- detección de causa raíz de routing mediante A/B;
- generación de un perfil runtime recomendado.

La arquitectura final del producto ya no depende de este runner para validar el Coach Copilot. El contrato canónico es:

```text
llm/COACH_COPILOT_CONTRACT.md
```

y el gate reproducible principal es:

```text
python -m llm.validate_coach_contract --db data/football_performance_synthetic_demo.duckdb
```

El smoke real final sobre la DuckDB profesional cerró con:

```text
SMOKE CONTRACT: PASS (28/28)
average_elapsed=0.4s
```

## Golden Set funcional

El runner genera un Golden Set dinámico usando jugadores y rivales reales de la DuckDB. Incluye:

- estado reciente del equipo;
- cambios/tendencia del equipo;
- jugador: rendimiento reciente;
- jugador: evolución;
- explicación de Match Rating reciente;
- separación Match Rating / Performance Index / motor experto;
- comparación descriptiva de jugadores;
- diferencias observables respetando rol y muestra;
- último partido;
- partido contra rival concreto;
- jugadores destacados descriptivamente en un partido;
- calidad/limitaciones de datos;
- GPS descriptivo;
- guardrail de once/titularidad;
- guardrail de fatiga;
- follow-up conversacional sobre un jugador.

Cada caso existe en castellano y catalán.

## Contrato de routing

El antiguo QA validaba principalmente que las tools necesarias estuvieran presentes. Eso podía dar PASS aunque hubiera tools sobrantes.

El contrato correcto valida simultáneamente:

```text
required_tools ⊆ actual_tools
actual_tools ⊆ allowed_tools
```

Por tanto distingue:

- `ROUTER_MISSING_TOOL`;
- `ROUTER_EXTRA_TOOL`;
- `ROUTER_WRONG_GUARDRAIL`.

El producto final añade además preflight determinista para evitar invocar un LLM ante ruido, meta-consultas o preguntas claramente fuera de dominio.

## A/B de causa raíz

Cuando una pregunta mutada falla routing:

1. se ejecuta la variante mutada;
2. se vuelve a ejecutar la pregunta Golden Set base;
3. si la base pasa y la mutación falla, se registra `mutation_trigger=true`;
4. se agrupa por mutación + tipo de fallo + tool extra/faltante.

Esto permite detectar automáticamente casos como una frase añadida que active una tool no deseada y evita atribuir ese problema a la síntesis LLM.

## QA de síntesis

Sobre los casos sintetizados se comprueba de forma determinista:

- runtime/error;
- fallback/timeout;
- tools usadas;
- grounding numérico;
- recomendaciones no autorizadas;
- idioma;
- máximo de seis frases;
- presencia del sujeto/jugador/rival cuando aplica.

No se afirma evaluar completamente utilidad técnica para entrenador ni corrección semántica total. Sigue siendo necesaria una revisión humana final de una muestra de respuestas cuando se modifica la arquitectura semántica.

## Búsqueda automática de perfil Ollama

Perfiles acotados:

```text
tiny
compact
fast
balanced
```

El proceso explora todos al inicio y después prioriza los que maximizan:

```text
reliability
- latency penalty
- runtime/fallback penalty
```

Con una pequeña exploración aleatoria para no quedar bloqueado por resultados iniciales.

Al finalizar guarda `recommended_profile.json` y `recommended_profile.env`.

## Capacidades actualmente soportadas fuera del runner

El runtime final ya incorpora de forma determinista:

- rankings por métricas queryables aprobadas;
- comparación entre jugadores;
- comparación por rol/posición;
- ventanas temporales;
- follow-ups ordinales y de evidencia;
- perfiles/evolución;
- partido/equipo;
- GPS descriptivo;
- calidad de datos;
- guardrails.

Para una pregunta como `¿Quién ha rendido mejor en la posición de central?`, el criterio de ordenación se declara explícitamente como **Match Rating medio dentro de la muestra del rol** y las demás métricas son evidencia descriptiva. No se crea un score nuevo.

## Capacidades que NO deben aprobarse todavía

Siguen siendo gaps reales de producto o investigación:

1. similitud de perfiles como capacidad de producto estable;
2. predicción de rendimiento futuro;
3. fatiga/readiness/riesgo de lesión;
4. XI ideal o selección automática;
5. recomendación táctica automática;
6. `mejor jugador`, `más completo` o `más determinante` sin criterio analítico explícito y validado.

Estas funciones necesitan primero analytics/modelos/policies validados downstream de DATA/ANALYTICS y no deben ser inventadas por el LLM.

## Ejecución opcional

Launcher Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\llm\start_agent_self_improve.ps1 -Hours 10
```

El launcher:

- usa `FPS_DB_PATH` si ya está definido;
- en el PC de desarrollo reconoce también la ruta local configurada;
- comprueba sintaxis Python antes de empezar;
- arranca Ollama si no está activo;
- verifica que el modelo exista;
- guarda transcript local;
- ejecuta el proceso con salida incremental.

No es necesario ejecutar este proceso para la entrega final mientras los contratos, CI y smoke real permanezcan en PASS.

## Artefactos

Directorio:

```text
outputs/agent_eval/self_improve/
```

Principales outputs:

```text
agent_self_improve_*_cases.jsonl
agent_self_improve_*_failures.csv
agent_self_improve_*_checkpoints.jsonl
agent_self_improve_*_summary.json
agent_self_improve_*_root_causes.json
agent_self_improve_*_golden_set.json
recommended_profile.json
recommended_profile.env
```

## Regla de seguridad

El runner no hace push, merge ni reescribe source code durante la ejecución. Tampoco cambia datos, features, ratings, thresholds, expert system ni modelos.

La salida del proceso sirve para una iteración humana posterior y para estudiar robustez lingüística; no sustituye los contratos reproducibles ni autoriza cambios automáticos en la lógica deportiva.
