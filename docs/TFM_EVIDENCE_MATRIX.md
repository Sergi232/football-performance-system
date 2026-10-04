# TFM — Matriz de evidencias y claims

Fecha: 04/10/2026

Objetivo: vincular cada afirmación relevante de la memoria con evidencia técnica reproducible del repositorio. Si un claim no aparece aquí o no dispone de evidencia independiente, no debe presentarse como resultado demostrado.

| Claim / resultado | Evidencia principal | Archivo / gate | Estado |
|---|---|---|---|
| El Collector V1.1 implementa la taxonomía aprobada | Validator final + tests contractuales | `collector/validate_collector_v1.py`, `tests/test_collector_contract.py` | PASS |
| La unidad analítica principal es jugador-partido | Esquema DuckDB | `data/schema.sql` | IMPLEMENTADO |
| FEATURE-01 genera 28 features base deterministas | Build + validator | `features/build_player_match_features.py`, `features/validate_stage1.py` | PASS |
| FEATURE-02 usa pasado estricto | Contrato temporal y validación | `features/build_temporal_features.py` | PASS |
| FEATURE-03 condiciona por rol observado sin inventarlo | Build + validación | `features/build_role_temporal_features.py` | PASS |
| Analytics separa self-role y peer-role evidence | Contrato ANALYTICS-01 | `analytics/build_stage1.py` | PASS |
| El sistema experto cubre N1000-N13000 | Builds/validators EXPERT-01..07 | `decision_tree/` | PASS |
| N9000 ignora GPS sintético como evidencia observada | Corrección + validator EXPERT-03 | `decision_tree/build_stage3.py`, `decision_tree/validate_stage3.py` | PASS |
| N13000 no emite recomendación sin policy validada | Recommendation gate | `decision_tree/build_stage7.py`, `tests/test_decision_tree_stage7.py` | PASS |
| Match Rating V5 cubre todas las apariciones jugadas | Contrato PERF-18 | `match_rating_v0.5-candidate` + validadores de rating | PASS |
| Match Rating y GPS permanecen separados | Arquitectura + access layer | `app/match_rating_access.py`, `app/gps_physical_access.py` | PASS |
| GPS es opcional y multi-proveedor | Contrato de normalización | `gps/`, `data/migrations/004_gps_normalization.sql` | PASS ESTRUCTURAL |
| GPS real tiene precedencia sobre sintético | Materialización del resumen físico | `analytics/build_gps_physical_summary.py` | PASS |
| No existen inferencias de fatiga/readiness/lesión | Guardrails de GPS, Attention, Expert y Assistant | `analytics/build_attention_flags.py`, `llm/coach_agent_fast.py` | PASS |
| Dashboard Team/Player/Match consume capas validadas | Data contract + QA de producto | `app/` validators | PASS |
| Access control restringe equipos por rol | Contract tests | `app/access_control.py` + validator | PASS |
| Autenticación real no está implementada | Estado explícito | `PROJECT_STATE.md` | LIMITACIÓN |
| Coach Copilot usa tools read-only y no recalcula métricas críticas | Arquitectura + contract tests | `llm/coach_agent_general.py`, `llm/coach_agent_fast.py` | PASS |
| Las consultas claras del Coach Copilot se resuelven de forma determinista | Smoke real + query grammar | `llm/smoke_test_coach_agent.py`, `llm/coach_agent_general.py` | PASS |
| El fallback local del Coach Copilot usa Qwen solo para lenguaje ambiguo | Runtime híbrido | `llm/coach_agent_general.py`, `llm/coach_agent_fast.py` | IMPLEMENTADO |
| Smoke local real del Coach Copilot cubre 22 casos | Ejecución con DuckDB profesional | `SMOKE CONTRACT: PASS (22/22)`, avg `1.4s` | PASS |
| Follow-ups ordinales/ventana/evidencia mantienen contexto | Smoke real + tests | `llm/smoke_test_coach_agent.py`, `tests/test_coach_agent_fast.py` | PASS |
| Guardrails bloquean fatiga, lesión, titularidad y criterios globales no validados | Smoke real + tests | `llm/coach_agent_fast.py`, `tests/test_coach_agent_fast.py` | PASS |
| OpenAI BYOK es opcional y no da acceso directo a DuckDB | Arquitectura externa | `llm/coach_agent_external.py`, `app/pages/5_Assistent_IA.py` | IMPLEMENTADO |
| Tool calls OpenAI se limitan y revalidan localmente | Contract tests | `tests/test_coach_agent_external.py` | PASS |
| Una tool externa desconocida se descarta | Contract test | `tests/test_coach_agent_external.py` | PASS |
| La API key del usuario no se persiste en DuckDB ni archivos del proyecto desde la UI | Implementación UI | `app/pages/5_Assistent_IA.py` | IMPLEMENTADO |
| El modo OpenAI ha sido probado live con una API key real | No existe evidencia live | — | NO VALIDADO |
| Reports V6 consumen analytics y no recalculan lógica crítica | Report gate | `reports/validate_reports_pro.py` | PASS |
| El producto completo supera QA end-to-end | Secuencia de validaciones por capas | `PROJECT_STATE.md` | PASS |
| La demo profesional local no se redistribuye por defecto | Política de publicación | `PROJECT_STATE.md`, `publication/` | LIMITACIÓN DE LICENCIA |
| Existe una demo pública generada desde cero | Builder sintético | `publication/build_synthetic_demo.py` | PASS |
| La demo sintética contiene 0 filas profesionales | Validator reproducible | `publication/validate_synthetic_demo.py` | PASS |
| La demo sintética funciona con la capa de app y reports | Validator reproducible | `app_read_layer=PASS`, `report_payloads=PASS` | PASS |
| La demo sintética es redistribuible según su contrato | Validator reproducible | `redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO` | PASS |
| El repo se valida desde un entorno limpio | GitHub Actions | `.github/workflows/tests.yml` | SUCCESS |
| CI se ejecuta en push/PR | Workflow GitHub Actions | `.github/workflows/tests.yml` | ACTIVO |

## Métricas de referencia del caso profesional de desarrollo

Estas cifras describen el caso técnico utilizado para validar el producto, no una muestra representativa del fútbol amateur:

```text
partidos de demo profesional = 38
apariciones jugadas = 590
jugadores en contexto producto = 36
Match Rating coverage = 590/590
Goalkeeper rating rows = 38
generic role fallback = 172
```

## Validación de referencia del Coach Copilot

```text
SMOKE CONTRACT = PASS (22/22)
average_elapsed = 1.4s
consultas deterministas típicas = 0.1–0.8s
follow-ups = 0.1–0.2s
fallback Qwen fuera de dominio observado = 25.3s
```

La latencia de 1,4 s es la media de esa batería concreta en el PC de desarrollo. No debe generalizarse como SLA universal.

## Métricas de la demo pública sintética

```text
demo_version = synthetic_public_demo_v0.1.0
matches = 12
players = 18
player_match = 216
played = 192
FEATURE-01 = 6048
FEATURE-02 = 42336
FEATURE-03 = 30456
analytics_rows = 12096
expert_rows = 39960
N13000 = 648
ratings = 192
performance_index = 192
gps = 192
professional_source_rows = 0
redistribution_status = REDISTRIBUTABLE_SYNTHETIC_DEMO
```

## Claims permitidos

Se puede afirmar:

- que se ha construido un prototipo end-to-end funcional;
- que la arquitectura es auditable por capas;
- que la demo sintética es reproducible desde código;
- que existen controles explícitos contra leakage temporal;
- que el sistema degrada cuando falta evidencia;
- que el LLM actúa downstream de analytics y decision engine;
- que las consultas soportadas de alta confianza pueden resolverse sin LLM;
- que el Coach Copilot pasó un smoke real de 22/22 casos sobre la DuckDB profesional;
- que existe un modo OpenAI BYOK opcional protegido por el mismo contrato de tools;
- que el QA técnico y CI están en PASS.

## Claims no demostrados

No afirmar como resultado probado:

- que el sistema mejore decisiones de entrenadores;
- que aumente victorias, puntos o rendimiento deportivo;
- que Match Rating represente una verdad objetiva universal;
- que GPS sintético valide carga fisiológica;
- que el sistema detecte fatiga, readiness o riesgo de lesión;
- que N13000 recomiende el rol táctico óptimo;
- que el producto tenga validación comercial real;
- que exista validación con usuarios reales si no se realiza posteriormente;
- que el modo OpenAI tenga una latencia o calidad concreta sin una prueba live;
- que una suscripción ChatGPT sustituya una API key o consumo API en el modo BYOK.

## Regla de uso en la memoria

Cada resultado cuantitativo importante debe poder responder a tres preguntas:

1. ¿de qué capa procede?;
2. ¿qué validator/test lo respalda?;
3. ¿qué limitación impide sobreinterpretarlo?

Si alguna de las tres respuestas falta, el claim debe rebajarse a observación, hipótesis futura o limitación.
