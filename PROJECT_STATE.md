# PROJECT_STATE

Última actualización: 03/10/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo junto con el código actual de `main`.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01                        CERRADO / V1.1 OFICIAL / FINAL GATE PASS
GPS-01 NORMALIZATION                CERRADO / VALIDADO ESTRUCTURALMENTE
GPS-DEMO SYNTHETIC                  CERRADO / VALIDADO EN DUCKDB
GPS PHYSICAL SUMMARY                CERRADO / VALIDADO / REAL > SYNTHETIC
FEATURE-01/02/03                    CERRADO / VALIDADO
ANALYTICS-01                        CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
PERF-18 MATCH RATING                CERRADO / VALIDADO / V5 ACTIVA
PERFORMANCE INDEX                   v0.2 EXPERIMENTAL / OPERATIVO
DASHBOARD TEAM / PLAYER / MATCH     OPERATIVO / QA PASS
DASHBOARD PHYSICAL / GPS            CERRADO / VALIDADO
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO v0.3
UI-PRESENTATION-ES-DEMO             CONTRACT PASS / DEMO MASKING ACTIVO
ACCESS-CONTROL-01                   CONTRACT PASS / AUTH REAL PENDIENTE
LLM-01                              CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / SMOKE 4/4 PASS
REPORTS-03 ELITE TECHNICAL REPORTS  CERRADO / V6 / GATE PASS
PUBLIC DEMO ANONYMIZED              CONTRACT PASS / REDISTRIBUCIÓN NO AUTORIZADA
PUBLIC DEMO SYNTHETIC               CERRADO / PASS / REDISTRIBUIBLE
REPRODUCIBILITY                     CERRADO / PASS
CI AUTOMÁTICO                       CERRADO / PASS
GLOBAL END-TO-END QA                CERRADO / PASS
TFM MEMORIA BASE                    BORRADOR TÉCNICO CREADO
TFM EVIDENCE MATRIX                 CREADA
FINAL-01                            PRODUCTO FUNCIONAL / REDACCIÓN ACADÉMICA
PUBLIC DEPLOYMENT                   NO HACER — derechos/licencia del dataset real no resueltos
```

## Hipótesis principal del TFM

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

La hipótesis está contrastada favorablemente en su dimensión técnica y arquitectónica mediante un prototipo funcional end-to-end.

No está demostrado y no debe afirmarse:
- que el sistema mejore objetivamente las decisiones del entrenador;
- que aumente el rendimiento deportivo;
- que GPS sintético valide fisiología real;
- fatiga, readiness/disponibilidad física o riesgo de lesión;
- capacidad clínica o preventiva;
- impacto comercial real sin validación de mercado.

La validación con entrenadores/analistas reales sería una mejora adicional, nunca evidencia simulada.

## Fuente de verdad

```text
código actual de main + commits recientes
→ PROJECT_STATE.md
→ docs/DECISIONS.md
→ docs/ARCHITECTURE.md
→ documentación específica del módulo
→ README.md / docs/WORKFLOW.md
→ conversaciones antiguas
```

## Arquitectura vigente

```text
COLLECTOR / IMPORT + GPS opcional
→ RAW / NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS
→ EXPERT SYSTEM / ML
→ PRODUCT SERVICE / ACCESS CONTROL
→ WEB DASHBOARD
   ↓              ↓
ASSISTANT IA      PDF
```

Regla global: ninguna capa superior puede inventar métricas, scores, clasificaciones o recomendaciones que no existan en una capa inferior validada.

LLM:

```text
DATA
→ ANALYTICS
→ DECISION ENGINE
→ READ-ONLY TOOLS
→ ROUTER
→ OLLAMA LOCAL
→ SEMANTIC GUARD
→ COACH
```

El LLM no calcula Match Rating, Performance Index, features críticas ni decisiones expertas.

## Variables aprobadas — Collector V1.1

Unidad principal: jugador-partido.

Identificación/contexto:
- jugador;
- dorsal editable;
- titular/suplente explícito;
- minutos;
- partido, equipo, rival, fecha;
- formación;
- rol/posición, lado y cambios de posición.

Eventos:
- pase completado/no completado;
- pase clave;
- asistencia;
- pase largo;
- centro;
- regate completado/fallado;
- pérdida;
- remate, remate a puerta, bloqueado, gol;
- entrada, intercepción, bloqueo, despeje;
- falta cometida/recibida con x/y;
- tarjeta amarilla/roja;
- penal provocado/concedido con resultado;
- parada y gol encajado;
- córner a favor/en contra con resultado posterior de ABP.

Reglas clave:
- `SHOT GOAL` y `SHOT ON_TARGET` cuentan en `A puerta`;
- una pasada `LONG` o `CROSS` ya cuenta en pase total;
- `PASS FAIL` y `DRIBBLE FAIL` generan pérdidas derivadas;
- no existe botón subjetivo `falta_peligrosa`;
- no se recogen manualmente métricas avanzadas derivables.

Taxonomía congelada: `collector/event_catalog.json`, `catalog_version=0.3.0`.

Validación responsive/mobile: contractual y estructural. No afirmar revisión visual real en múltiples dispositivos si no se ha realizado.

## Data / Feature / Analytics

Data Layer:
- DuckDB;
- unidad jugador-partido;
- raw stats separados de features y decisiones;
- 38 partidos de demo;
- 590 apariciones jugadas;
- 36 jugadores en el contexto de producto.

FEATURE-01:
- 28 features base;
- ratios en [0,1];
- per-90 no negativos;
- NULL preservado según contrato.

FEATURE-02:
- operadores temporales strict-past;
- sin información futura.

FEATURE-03:
- contexto por rol observado;
- no inferencia de rol faltante.

ANALYTICS-01:
- `SELF_ROLE_PRIOR` y `PEER_ROLE_PRIOR` separados;
- peer pool strict-past;
- jugador actual excluido;
- ponderación igual por peer;
- no crea score/ranking/recomendación.

## Rendimiento

```text
MATCH RATING
= nota inmediata jugador-partido
= disponible desde partido 1
= match_rating_v0.5-candidate

PERFORMANCE INDEX
= capa histórica/posicional complementaria
= performance_score_v0.2-experimental
= no sustituye Match Rating
```

Match Rating V5 permanece congelado. No modificar fórmula, pesos o arquitectura sin nueva evidencia, experimento explícito y validación.

Baseline V5 validado:
- 590/590 apariciones;
- 38/38 partidos;
- 380 outfield `PERF18_ANCHORED`;
- 38 porteros con ruta específica;
- 172 fallback explícito por rol no disponible;
- nulls=0;
- duplicates=0;
- out_of_range=0.

## Expert System N1000-N13000

Familias:
- N1000 disponibilidad/actividad;
- N2000 perfil estructural;
- N3000 forma/evolución;
- N4000 amenaza ofensiva;
- N5000 creación/progresión;
- N6000 contribución defensiva;
- N7000 finalización;
- N8000 contexto del equipo;
- N9000 componente físico;
- N10000 rol/contexto;
- N11000 consistencia/tendencia;
- N12000 player fit evidence;
- N13000 gate de recomendación.

Cada nodo mantiene entrada → condición → resultado → confianza → justificación.

N13000 no emite una recomendación táctica sin policy validada.

### Corrección N9000 cerrada

El experto solo considera GPS **observado no sintético** como evidencia física.

La demo GPS sintética queda excluida de N9000 y de cualquier recomendación/decisión experta.

Corrección validada en:
- `decision_tree/build_stage3.py`;
- `decision_tree/validate_stage3.py`.

Estado de la DB actual:
- observaciones GPS reales/no sintéticas para experto: 0;
- `Synthetic demo GPS is excluded from expert evidence: PASS`.

## GPS

Flujo canónico:

```text
archivo proveedor / synthetic demo
→ gps_imports
→ gps_player_map
→ gps_observations
→ analytics/build_gps_physical_summary.py
→ player_match_gps_summary
→ app/gps_physical_access.py
→ dashboard Físico / GPS
→ reports V6
```

Resumen activo: `gps_physical_summary_v0.1-descriptive`.

Demo:
- `gps_synthetic_demo_v1.2.0`;
- provider `FPS Synthetic Demo`;
- source `SYNTHETIC_DEMO_NOT_OBSERVED`;
- 38 imports;
- 590 mappings;
- 38197 observaciones;
- 590 summaries/latest.

Precedencia:

```text
GPS REAL / observado
→ prioridad sobre synthetic para el mismo jugador-partido
→ imported_at solo desempata dentro de la misma clase
```

No existen umbrales canónicos de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

GPS no modifica Match Rating, Performance Index ni decisiones expertas.

## Dashboard / producto

### Equipo
Match Rating V5, forma, plantilla, tendencias descriptivas, participación, Performance Index, historial, GPS y PDF.

### Jugador
Match Rating V5, confianza, perfil, Performance Index, dimensiones, evolución, motor experto, partidos, GPS y PDF.

### Partido
Ratings V5, confianza, roles, minutos, observaciones deterministas, GPS y PDF.

### Físico / GPS
Capa descriptiva opcional; demo sintética explícitamente etiquetada.

### Alertas
Solo estados auditables de contexto/calidad. No fatiga, lesión ni good/bad performance thresholds.

### Demo / presentación
`FPS_DEMO_MODE=1` por defecto:
- equipo → `Equipo Demo`;
- jugadores → `Jugador 01...`;
- rivales → `Rival 01...`.

IDs y datos internos no se alteran.

### Access control
- SUPERADMIN → todos los equipos;
- CLUB_ADMIN → equipos autorizados;
- STAFF → equipos asignados.

Autenticación real email/contraseña/sesiones: no implementada todavía.

## LLM-02 — Local Coach Copilot — CERRADO MVP

Versión oficial del MVP: castellano.

Arquitectura:

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ router determinista
→ compact evidence
→ Ollama qwen3:1.7b
→ semantic guard
→ Coach Copilot
```

Gate ES previamente cerrado:
- router 17/17;
- full aggregate 66/68 = 97.1%;
- runtime errors=0;
- safety failures=0;
- numeric grounding PASS;
- castellano PASS;
- subject contract PASS;
- latencia media <=12s PASS.

Limitación menor aceptada: 2/68 challenge cases excedieron el límite formal de frases.

No validados:
- ranking por rol;
- similitud de jugadores;
- predicción futura;
- XI ideal;
- recomendaciones tácticas automáticas;
- fatiga/readiness/riesgo de lesión.

### Contrato operativo Ollama — 03/10/2026

Perfil local validado:

```text
model=qwen3:1.7b
scope=SPANISH_ONLY_MVP
thinking=False
FPS_AGENT_NUM_CTX=1536
FPS_AGENT_TIMEOUT=18
keep_alive=30m
```

Regla operativa importante:
- el warm-up del validator debe usar el **mismo `num_ctx` que producción**;
- usar warm-up `512` y runtime `1536` obliga a Ollama CPU a recargar el runner/model context y puede hacer que la primera síntesis llegue al timeout de 18 s;
- `llm/validate_local_agent.py` quedó corregido para alinear warm-up y runtime;
- commit de corrección: `f53efa8`;
- si `/api/tags` queda bloqueado localmente, reiniciar Ollama es una acción operativa válida; no implica regresión del producto.

Smoke final local confirmado:

```text
ollama_available=True
model=qwen3:1.7b
scope=SPANISH_ONLY_MVP
thinking=False | num_ctx=1536
ollama_warmup=PASS
team_grounding_es=PASS
quality_grounding_es=PASS
guardrail_lineup_es=PASS
guardrail_fatigue_es=PASS
LOCAL AGENT CONTRACT: PASS (4/4)
```

No reabrir LLM-02 por una incidencia local de arranque/latencia salvo evidencia de fallo funcional del contrato aprobado.

## Reports V6

Capa activa:

```text
reports/report_metrics.py          → report_descriptive_v0.2
reports/data_builder.py            → schema 0.7.0
reports/pdf_engine_elite_v6.py     → renderer activo
reports/pdf_engine_es.py           → wrapper app
reports/validate_reports_pro.py    → gate técnico
```

Team: 4 páginas. Player: 3 páginas. Match: 3 páginas.

Principios:
- consume analytics materializados;
- no recalcula Match Rating, Performance Index ni experto;
- GPS descriptivo y opcional;
- synthetic demo explícitamente etiquetada;
- sin claims de fatiga, lesión o readiness.

Gate V6: PASS técnico y revisión visual sin clipping/overlap grave.

## Global end-to-end QA — CERRADO 03/10/2026

QA ejecutado sobre la DB local actual y `main`.

### Fase 1 — Data/core
- Collector V1.1: PASS;
- Database validation: PASS;
- FEATURE-01: PASS;
- FEATURE-02: PASS;
- Match Rating V5: PASS;
- GPS Physical Summary: PASS.

### Fase 2 — Analytics / Expert
- FEATURE-03: PASS;
- ANALYTICS-01: PASS;
- EXPERT-01: PASS;
- EXPERT-02: PASS;
- EXPERT-03: PASS tras corregir semántica N9000 observed-only;
- EXPERT-04: PASS;
- EXPERT-05: PASS;
- EXPERT-06: PASS;
- EXPERT-07 / N13000: PASS.

### Fase 3A — Producto
- Dashboard data contract: PASS;
- Streamlit UI compatibility: PASS;
- Demo/castellano/anonymization: PASS;
- Access control: PASS;
- Attention Centre: PASS;
- Match Mode: PASS.

### Fase 3B — Entrega
- LLM-01 assistant contract: PASS;
- Coach Copilot local: PASS 4/4;
- Reports V6: PASS;
- Public Demo anonymized contract: PASS.

Resultado:

```text
GLOBAL END-TO-END QA: PASS
```

Cadena validada:

```text
Collector
→ DuckDB
→ Features
→ Analytics
→ Match Rating
→ GPS
→ Expert N1000-N13000
→ Dashboard
→ Access control
→ Demo presentation
→ Coach Copilot
→ PDF
→ Public-demo anonymization
```

La exportación demo anonimizada no concede derechos de redistribución del dataset fuente.

## Reproducibilidad pública + CI — CERRADO 03/10/2026

Se ha separado formalmente el caso profesional privado de una demo pública sintética reproducible.

### Demo sintética pública

Builder/validator:
- `publication/build_synthetic_demo.py`;
- `publication/validate_synthetic_demo.py`.

Gate local confirmado:

```text
SYNTHETIC PUBLIC DEMO CONTRACT: PASS
demo_version=synthetic_public_demo_v0.1.0
matches=12
players=18
player_match=216
played=192
FEATURE-01=6048
FEATURE-02=42336
FEATURE-03=30456
analytics_rows=12096
expert_rows=39960
N13000=648
ratings=192
performance_index=192
gps=192
app_read_layer=PASS
report_payloads=PASS
professional_source_rows=0
redistribution_status=REDISTRIBUTABLE_SYNTHETIC_DEMO
```

La demo se genera desde cero y no copia filas, nombres, IDs ni provenance del caso profesional.

Match Rating V5 y Performance Index en esta demo pública son **fixtures sintéticos de compatibilidad de producto**, no una revalidación científica de los modelos calibrados sobre el caso profesional.

### CI automático

Workflow activo: `.github/workflows/tests.yml`.

Triggers:
- `push`;
- `pull_request`;
- `workflow_dispatch`.

El CI ejecuta en Ubuntu/Python 3.13:
1. instalación de dependencias;
2. `pytest -q`;
3. construcción y validación completa de la demo sintética pública.

Primera ejecución automática: FAIL de entorno porque el runner no tenía la raíz del repo en `PYTHONPATH`; no fue un fallo funcional del producto.

Corrección: commit `894740e` (`Fix CI Python import path`).

Ejecución posterior confirmada:

```text
GitHub Actions run 37081464123
Install dependencies: PASS
Run unit and contract tests: PASS
Build and validate synthetic public demo: PASS
Conclusion: SUCCESS
```

Esto demuestra que el repositorio puede validarse desde un entorno limpio sin depender de la DuckDB privada del desarrollador.

## Memoria académica — EN REDACCIÓN

Se han creado dos documentos base:

- `docs/TFM_MEMORIA_BASE.md`: narrativa técnica inicial de la memoria en castellano;
- `docs/TFM_EVIDENCE_MATRIX.md`: matriz que vincula claims, gates, archivos y limitaciones.

La memoria base ya contiene:
- problema y motivación;
- hipótesis y objetivos;
- metodología;
- Collector;
- modelo de datos;
- Feature Engine;
- Analytics;
- sistema experto N1000-N13000;
- Match Rating y Performance Index;
- GPS;
- dashboard;
- Coach Copilot;
- PDF;
- validación y reproducibilidad;
- resultados;
- limitaciones;
- conclusiones y trabajo futuro.

Regla de redacción: ningún resultado académico importante puede aparecer sin soporte técnico rastreable en la matriz de evidencias.

## Experimentos / decisiones relevantes

- Collector V1.1 congelado sobre `event_catalog v0.3.0`;
- Match Rating V5 validado y congelado;
- Performance Index separado del Match Rating;
- sistema experto jerárquico preferido frente a un único `DecisionTreeClassifier`;
- línea ML de posición cerrada como context-only al superar una regla simple al modelo;
- LLM downstream y sin acceso directo a DB;
- idioma oficial del MVP LLM: castellano;
- control de acceso separado de autenticación;
- PDF downstream de analytics;
- GPS real y synthetic comparten capa canónica;
- GPS real tiene precedencia;
- synthetic GPS no alimenta Match Rating, Performance Index ni decisiones expertas;
- no inferir posición específica para suplentes sin dato observacional;
- hipótesis principal = viabilidad técnica/auditable, no mejora causal del rendimiento;
- demo pública final separada del caso profesional mediante generación sintética desde cero;
- CI automático obligatorio para evitar regresiones en `main`.

## Decisiones descartadas / aplazadas

- optimización indefinida de qwen3:1.7b: descartada MVP;
- LLM bilingüe CA+ES: descartado MVP;
- confiar solo en pass rate automático: descartado;
- modificar DB real para anonimizar: descartado;
- XI ideal/predicción/fatiga/lesión sin policy analítica validada: no permitido;
- inferir rol para suplentes sin evidencia: descartado;
- login SaaS completo/pagos/password recovery: aplazado;
- publicación del dataset real: bloqueada por derechos/licencia;
- PDF como captura literal de la web: descartado;
- copiar métricas/layouts propietarios: descartado;
- inventar validación de usuarios: no permitido.

## Problemas abiertos

- adaptar `docs/TFM_MEMORIA_BASE.md` a la plantilla/rúbrica formal de la universidad cuando esté disponible;
- incorporar bibliografía y marco teórico con fuentes académicas verificables;
- completar tablas/figuras/capturas académicas y anexos;
- revisión final/archivo de documentación histórica secundaria si aporta claridad al repositorio;
- defensa y demo final;
- autenticación real si el producto evoluciona a uso comercial;
- derechos/licencia antes de cualquier despliegue público del dataset profesional;
- validación con GPS real y usuarios reales si se dispone de datos/participantes autorizados.

## Siguiente paso exacto

1. convertir `docs/TFM_MEMORIA_BASE.md` en memoria académica definitiva adaptada a la plantilla/rúbrica oficial;
2. construir marco teórico y bibliografía verificable para justificar decisiones, métricas y arquitectura;
3. completar metodología/resultados utilizando `docs/TFM_EVIDENCE_MATRIX.md` como control de claims;
4. preparar figuras, tablas, capturas y anexos reproducibles;
5. hacer revisión final del repositorio y archivar documentación histórica que pueda confundir sin perder trazabilidad;
6. preparar defensa y demo final;
7. Power BI, validación comercial, autenticación completa o nuevos módulos solo como complementos si queda margen.