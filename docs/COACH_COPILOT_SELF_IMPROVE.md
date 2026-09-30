# Coach Copilot — Self-Improve QA

Estado: implementado para ejecución local no supervisada.

## Objetivo

Mejorar la robustez del Coach Copilot sobre casos de uso reales de entrenador sin permitir que el proceso modifique automáticamente analytics, Match Rating, Performance Index, sistema experto, reglas de decisión ni pesos del modelo.

No es fine-tuning. La mejora automática se limita a:

- selección adaptativa de casos débiles;
- replay de fallos;
- variaciones lingüísticas ES/CA que preservan la intención;
- búsqueda controlada del mejor perfil de síntesis Ollama;
- detección de causa raíz de routing mediante A/B;
- generación de un perfil runtime recomendado.

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

El nuevo contrato valida simultáneamente:

```text
required_tools ⊆ actual_tools
actual_tools ⊆ allowed_tools
```

Por tanto distingue:

- `ROUTER_MISSING_TOOL`;
- `ROUTER_EXTRA_TOOL`;
- `ROUTER_WRONG_GUARDRAIL`.

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

No se afirma evaluar completamente utilidad técnica para entrenador ni corrección semántica total. Sigue siendo necesaria una revisión humana final de una muestra de respuestas.

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

## Capacidades que NO deben aprobarse todavía

El proceso registra como gaps de producto, no como fallos del LLM:

1. ranking condicionado por rol, por ejemplo `¿Quién rinde mejor como interior?`;
2. similitud de perfiles entre jugadores;
3. predicción de rendimiento futuro.

Estas funciones necesitan primero analytics/modelos validados downstream de DATA/ANALYTICS y no deben ser inventadas por el LLM.

## Ejecución

Launcher Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\llm\start_agent_self_improve.ps1 -Hours 10
```

El launcher:

- usa `FPS_DB_PATH` si ya está definido;
- en el PC actual reconoce también `D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb`;
- comprueba sintaxis Python antes de empezar;
- arranca Ollama si no está activo;
- verifica que el modelo exista;
- guarda transcript en el Escritorio;
- ejecuta el proceso con salida incremental.

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

La salida del proceso sirve para la siguiente iteración humana de código y para decidir el runtime profile final del Coach Copilot.
