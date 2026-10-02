# PROJECT_STATE

Última actualización: 02/10/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo junto con el código actual de `main`.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE / UX+ES+MÓVIL PENDIENTE
GPS-01 NORMALIZATION                CERRADO / VALIDADO ESTRUCTURALMENTE
GPS-DEMO SYNTHETIC                  CERRADO / VALIDADO EN DUCKDB
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01                              PROTOTYPE v0.1 / CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / LIMITACIÓN MENOR DOCUMENTADA
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         BASELINE CERRADO / GATE TÉCNICO + VISUAL PASS
REPORTS-03 ELITE TECHNICAL REPORTS  CERRADO / V5 / GATE TÉCNICO + VISUAL PASS
DASHBOARD-01                        CONTRACT PASS
DASHBOARD PROFESSIONAL REDESIGN     IMPLEMENTADO
UI-PRESENTATION-ES-DEMO             CONTRACT PASS / DEMO MASKING ACTIVO
ACCESS-CONTROL-01                   CONTRACT PASS / AUTH REAL PENDIENTE
ARCHITECTURE-01                     CERRADO
ANALYTICS-01                        CERRADO / VALIDADO
DECISION POLICY / N13000            GATE APROBADO
PERF-18 MATCH RATING DATA SCIENCE   CERRADO / VALIDADO — V5 ACTIVA
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              OPERATIVO / MATCH RATING V5 INTEGRADO
MATCH MODE                          CONTRACT PASS / OPERATIVO DESDE PARTIDO 1
DASHBOARD-04 PHYSICAL/GPS           CERRADO / VALIDADO / DEMO SINTÉTICA DISPONIBLE
ALERTS-01 ATTENTION CENTRE          CERRADO / VALIDADO — v0.3
UI COMPATIBILITY                    PASS
FINAL-01                            ACTIVO / PRODUCTO FINAL
PUBLIC DEPLOYMENT                   NO HACER — derechos/licencia no resueltos
```

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

## Arquitectura actual

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

La web es el producto principal. Los PDF son informes técnicos profesionales complementarios para el cuerpo técnico.

Regla global: ninguna capa superior puede inventar métricas, scores, clasificaciones o recomendaciones que no existan en una capa inferior validada.

## Variables / datos aprobados para el MVP

Unidad principal: jugador-partido.

Collector funcional actual:
- identificación: jugador, dorsal, rol/posición, titular/suplente, minutos;
- pase: completada, no completada, pase clave, asistencia;
- progresión: centro, pase largo;
- 1v1: regate completado, pérdida;
- finalización: remate, remate a puerta, bloqueado, gol;
- defensa: entrada, intercepción, bloqueo;
- disciplina: falta cometida, falta recibida, tarjeta, penal;
- portero: parada, gol encajado;
- contexto: rol/posición, lado, formación, cambio de posición;
- equipo/ABP: córners y faltas peligrosas a favor/en contra, con resultado posterior cuando exista en la fuente.

GPS es opcional y se normaliza a esquema común. No se recogen manualmente métricas avanzadas derivables.

## GPS — estado validado

Flujo canónico:

```text
archivo proveedor / generador demo
→ gps_imports
→ gps_player_map
→ gps_observations
→ analytics/build_gps_physical_summary.py
→ player_match_gps_summary
→ app/gps_physical_access.py
→ dashboard Físico / GPS
→ reports (integración física pendiente)
```

Demo sintética activa:

```text
generator_version=gps_synthetic_demo_v1.2.0
provider=FPS Synthetic Demo
source=SYNTHETIC_DEMO_NOT_OBSERVED
appearances=590
imports=38
player_maps=590
observations=38197
summary_rows=590
latest_rows=590
sample_seconds=60
```

La demo es determinista y sirve exclusivamente para demostrar el producto cuando no hay GPS real aprobado. No constituye una validación fisiológica ni una norma deportiva.

Condicionamiento validado:
- minutos jugados: sí;
- rol/posición cuando la fuente lo permite: sí;
- correlación minutos-distancia observada en la demo: 0.9225;
- rango distancia respecto al prior rol+minutos: 0.840..1.148;
- duplicados de muestras: 0;
- duplicados de resúmenes latest: 0;
- procedencia sintética explícita: PASS.

Familias físicas demo:
`GK`, `CB`, `FB`, `CM`, `AM_W`, `ST`, `OTHER`.

Cobertura posicional:
- 482/590 apariciones (81.7%) tienen rol resoluble desde `primary_role` o `default_position`;
- 108/590 (18.3%) no tienen posición recuperable: tanto `primary_role` como `default_position` indican `Substitute`;
- esas 108 apariciones permanecen en `OTHER` y usan un prior genérico de demo;
- no se les asigna una posición específica inventada ni se debe interpretar su valor como comparación posicional.

No se han introducido umbrales de HSR, sprint, workload, fatiga, readiness o riesgo de lesión.

GPS no modifica Match Rating, Performance Index ni decisiones del sistema experto.

## Rendimiento vigente

```text
MATCH RATING
= nota inmediata jugador-partido
= disponible desde partido 1
= versión activa match_rating_v0.5-candidate

PERFORMANCE INDEX
= capa histórica/posicional complementaria
= performance_score_v0.2-experimental
= no sustituye Match Rating
```

Match Rating V5 permanece congelado. No modificar fórmula, pesos o arquitectura sin nueva evidencia, experimento explícito y validación.

## Gates principales validados

```text
MATCH RATING CONTRACT: PASS
590/590 apariciones valoradas
38/38 partidos
nulls=0
duplicates=0
out_of_range=0

GPS SYNTHETIC DEMO CONTRACT: PASS
generator_version=gps_synthetic_demo_v1.2.0
canonical_flow=PASS
player_match_linkage=PASS
duplicate_samples=0
duplicate_latest_summaries=0

GPS SYNTHETIC COHERENCE AUDIT: PASS
scope=INTERNAL_DEMO_COHERENCE_NOT_PHYSIOLOGICAL_VALIDATION
minutes_conditioning=PASS
role_conditioning=PASS
synthetic_provenance=PASS

DEMO PRESENTATION: PASS
team=Equipo Demo
players_masked=36
opponents_masked=19
catalan_visible_strings=0

ACCESS CONTROL: PASS
superadmin=PASS
staff_single_team=PASS
staff_unauthorized_query_blocked=PASS
restricted_without_assignment_fail_closed=PASS
club_admin_scope=PASS

REPORTS ELITE TECHNICAL GATE V5: PASS
schema=0.6.0
report_metrics=report_descriptive_v0.2
spanish=PASS
anonymization=PASS
technical_context=PASS
materialized_match_summary=PASS
critical_recalculation_guard=PASS

ATTENTION FLAGS CONTRACT: PASS
MATCH MODE CONTRACT: PASS
DASHBOARD-01 DATA CONTRACT: PASS
N13000 recommendation gate safety: PASS
```

## LLM-02 — Local Coach Copilot — CERRADO MVP

Arquitectura:

```text
DuckDB local
→ analytics / expert system materializados
→ tools Python read-only
→ router determinista
→ compact evidence
→ Ollama qwen3:1.7b
→ semantic guard determinista
→ Coach Copilot
```

El LLM no accede directamente a DuckDB y no calcula Match Rating, Performance Index, features críticas ni decisiones expertas.

Gate final ES: router 17/17; full aggregate 66/68 = 97.1%; runtime errors=0; safety failures=0; numeric grounding PASS; castellano PASS; subject contract PASS; latencia media <=12s PASS.

Limitación menor aceptada: 2/68 casos challenge incumplieron el límite formal de frases. No reabrir LLM-02 salvo error funcional grave.

No validados: ranking por rol, similitud de jugadores, predicción futura, XI ideal, recomendaciones tácticas automáticas, fatiga/readiness/riesgo de lesión.

## UI / demo / anonimización

`app/presentation.py` implementa anonimización exclusivamente de presentación.

```text
FPS_DEMO_MODE=1  → modo demo por defecto
Equipo real       → Equipo Demo
jugadores reales  → Jugador 01, Jugador 02, ...
rivales reales    → Rival 01, Rival 02, ...
```

IDs, datos, Match Rating, Performance Index y motor experto permanecen intactos.

La UI principal está en castellano: Home, Equipo, Jugador, Partido, Performance Index, Físico/GPS, Calidad y alertas, Asistente IA.

## ACCESS-CONTROL-01

```text
SUPERADMIN  → todos los equipos
CLUB_ADMIN  → equipos autorizados del club
STAFF       → equipos asignados
```

La capa de datos filtra equipos autorizados y bloquea consultas directas a `team_id` ajenos. Un usuario restringido sin asignaciones falla cerrado.

Autenticación real email/contraseña/sesiones NO implementada todavía. Está separada de autorización y documentada en `docs/ACCESS_CONTROL.md`.

La base demo actual contiene un solo equipo, por lo que el contrato multi-equipo se valida estructuralmente, no mediante una demo visual con varios clubes.

## REPORTS-03 — ELITE TECHNICAL REPORTS — CERRADO BASELINE

Los informes son técnicos y staff-facing; no son una captura literal de la web.

Capa activa:

```text
reports/report_data_access.py
→ agregados raw jugador-partido → equipo-partido
reports/report_metrics.py
→ report_descriptive_v0.2
reports/data_builder.py
→ schema 0.6.0
reports/pdf_engine_elite_v5.py
→ renderer activo
reports/pdf_engine_es.py
→ wrapper usado por la app
```

Principios cerrados:
- cambio temporal antes que ranking;
- métricas transparentes junto al Match Rating;
- deltas descriptivos sin etiquetar automáticamente bueno/malo;
- no inventar xG, posesión, pressures, pass networks, heatmaps o tracking sin datos válidos;
- Match Report compara solo con historia anterior, nunca futura;
- el PDF no recalcula Match Rating, Performance Index ni decisiones expertas.

V5 incorpora pulso Team `Último / Últimos 10 / Todos / Δ 10 vs todos` y claves deterministas de revisión técnica.

La extensión física GPS todavía NO está conectada a los PDFs.

## Producto actual

### Home / Centro de mando
Último partido, brief operativo, forma, tendencias, cambios, ratings, calidad de datos y navegación.

### Jugador
Match Rating V5, confianza, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF V5.

### Equipo
Match Rating V5, forma, mapa de plantilla, tendencias, participación, Performance Index, historial y PDF V5.

### Partido
Ratings V5, confianza, roles, minutos, dimensiones, observaciones deterministas y PDF V5.

### Físico / GPS
Capa opcional descriptiva operativa. La demo sintética canónica está disponible y explícitamente etiquetada como no observada.

### Alertas
Solo estados auditables de contexto/calidad.

## Collector — pendiente de producto/UX

Funcionalmente cerrado; falta:
1. simplificar interfaz de captura;
2. castellano completo;
3. mobile-first / responsive;
4. reducir clics y fricción durante 90 minutos;
5. mantener exactamente la semántica y compatibilidad del esquema actual;
6. no añadir nuevas variables sin justificar recogibilidad y uso final.

## Experimentos / decisiones relevantes

- Match Rating V5 validado y congelado;
- Performance Index separado del Match Rating;
- sistema experto jerárquico preferido frente a un único `DecisionTreeClassifier`;
- LLM downstream y sin acceso directo a DB;
- demo anonimizada solo en presentación, no en base de datos;
- control de acceso separado de autenticación;
- PDFs consumen analytics materializados y no recalculan métricas críticas;
- GPS real y GPS demo comparten la capa canónica normalizada;
- demo GPS sintética condicionada por minutos y rol cuando el rol está disponible;
- no inferir una posición de partido cuando la fuente solo informa `Substitute`;
- GPS sintético no alimenta Match Rating, Performance Index ni decisiones expertas;
- PDF final = informe técnico profesional independiente, no reproducción literal de la web.

## Decisiones descartadas / aplazadas

- seguir optimizando indefinidamente qwen3:1.7b: descartado MVP;
- LLM bilingüe CA+ES: descartado MVP, castellano oficial;
- confiar solo en pass rate automático: descartado;
- modificar DuckDB para anonimizar: descartado;
- XI ideal / predicciones / fatiga / lesión sin capa analítica validada: no permitido;
- inferir rol específico para suplentes sin dato observacional suficiente: descartado;
- login SaaS completo, pagos y recuperación de contraseña: aplazado tras el MVP;
- publicación pública del dataset real: bloqueada por derechos/licencia;
- PDF como simple captura de la web: descartado;
- copiar métricas/layouts propietarios de Opta/Wyscout/StatsBomb: descartado.

## Problemas abiertos

- integrar la capa física GPS descriptiva en PDF Team / Player / Match;
- mantener etiqueta explícita de GPS sintético en demo;
- no convertir GPS descriptivo en claims de fatiga/readiness/lesión;
- Collector UX / castellano / móvil;
- autenticación real para producto comercial;
- QA global final;
- documentación final del TFM;
- derechos/licencia antes de despliegue público.

## Siguiente paso exacto

1. conectar `player_match_gps_summary` a `reports/data_builder.py` mediante acceso read-only;
2. añadir bloques físicos descriptivos a Team / Player / Match PDF V5;
3. añadir `Claves para la revisión física` deterministas y trazables;
4. etiquetar claramente `GPS sintético / DATOS DEMO` cuando el proveedor sea `FPS Synthetic Demo`;
5. no introducir fatiga, readiness, riesgo de lesión, HSR o sprint thresholds;
6. extender `reports/validate_reports_pro.py` y pasar gate técnico;
7. después retomar Collector UX y QA global.
