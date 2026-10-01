# PROJECT_STATE

Última actualización: 01/10/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo junto con el código actual de `main`.

## Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE / UX+ES+MÓVIL PENDIENTE
GPS-01                              CERRADO / VALIDADO ESTRUCTURALMENTE
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01                              PROTOTYPE v0.1 / CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / LIMITACIÓN MENOR DOCUMENTADA
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         BASELINE CERRADO / GATE TÉCNICO + VISUAL PASS
REPORTS-03 ELITE TECHNICAL REPORTS  ACTIVO / RESEARCH + IMPLEMENTACIÓN HECHA / GATE PENDIENTE
DASHBOARD-01                        CONTRACT PASS
DASHBOARD PROFESSIONAL REDESIGN     IMPLEMENTADO
UI-PRESENTATION-ES-DEMO             CONTRACT PASS / DEMO MASKING ACTIVO
ACCESS-CONTROL-01                   CONTRACT PASS / AUTH REAL PENDIENTE
PRODUCT-SPIRAL-01                   PREPARADO — UI/PDF SAFE AUTO-IMPROVEMENT + REGRESSION QA
ARCHITECTURE-01                     CERRADO
ANALYTICS-01                        CERRADO / VALIDADO
DECISION POLICY / N13000            GATE APROBADO
PERF-18 MATCH RATING DATA SCIENCE   CERRADO / VALIDADO — V5 ACTIVA
SCORE-INTEGRATION-01                v0.2 VALIDADA / CONTRACT PASS
DASHBOARD-02 PLAYER VIEW            CERRADO / VALIDADO VISUALMENTE
DASHBOARD-03 TEAM MODE              OPERATIVO / MATCH RATING V5 INTEGRADO
MATCH MODE                          CONTRACT PASS / OPERATIVO DESDE PARTIDO 1
DASHBOARD-04 PHYSICAL/GPS           CERRADO / VALIDADO
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

REPORTS PROFESSIONAL GATE: PASS
schema=0.5.0
spanish=PASS
anonymization=PASS
materialized_match_summary=PASS
critical_recalculation_guard=PASS
Team / Player / Match generados
human visual gate=PASS

REPORTS-03 ELITE TECHNICAL GATE
schema=0.6.0
report_metrics=report_descriptive_v0.1
estado=PENDIENTE DE EJECUCIÓN LOCAL + GATE VISUAL

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

Gate final ES:

```text
router=17/17 = 100%
full aggregate=66/68 = 97.1%
runtime errors=0
safety failures=0
numeric grounding=PASS
Spanish language=PASS
subject contract=PASS
latencia media <=12s=PASS
```

Limitación menor aceptada: 2/68 casos challenge incumplieron el límite formal de frases. No reabrir LLM-02 salvo error funcional grave.

Capacidades NO validadas: ranking por rol, similitud de jugadores, predicción futura, XI ideal, recomendaciones tácticas automáticas, fatiga/readiness/riesgo de lesión.

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

Arquitectura preparada para producto multi-tenant:

```text
SUPERADMIN  → todos los equipos
CLUB_ADMIN  → equipos autorizados del club
STAFF       → equipos asignados
```

La capa de datos filtra equipos autorizados y bloquea consultas directas a `team_id` ajenos. Un usuario restringido sin asignaciones falla cerrado.

Autenticación real email/contraseña/sesiones NO implementada todavía. Está separada de autorización y documentada en `docs/ACCESS_CONTROL.md`.

La base demo actual contiene un solo equipo, por lo que el contrato multi-equipo se valida estructuralmente, no mediante una demo visual con varios clubes.

## REPORTS-02 — BASELINE CERRADO

Objetivo aprobado: informes técnicos profesionales independientes para el cuerpo técnico. No son una captura de la web ni un volcado de tablas.

Baseline validada:
- schema `0.5.0`;
- castellano y anonimización;
- Team 3 páginas, Player 2, Match 2;
- gate automático y visual PASS.

Se conserva como referencia estable y fallback de la fase anterior.

## REPORTS-03 — ELITE TECHNICAL REPORTS — ACTIVO

Motivo de reapertura: elevar el producto desde un informe profesional correcto a un informe diseñado explícitamente según flujos y preferencias documentadas de cuerpos técnicos.

Investigación documentada en `docs/REPORT_DESIGN_RESEARCH.md` con referencias públicas a:
- Opta / Stats Perform ProVision;
- Hudl Wyscout Reports;
- Hudl StatsBomb;
- UEFA Technical Reports / Performance Insights;
- Catapult para reporting físico;
- estudios de practitioners sobre KPI y visualización.

Principios adoptados:
- cambio temporal antes que ranking;
- raw / transparent metrics junto al Match Rating;
- línea para evolución, cuadrante para plantilla, barras/tablas para comparación y trazabilidad;
- KPI contextualizados por posición;
- no crear rojo/verde como juicio bueno/malo para deltas descriptivos;
- no inventar xG, posesión, pressures, pass networks, heatmaps o tracking sin datos válidos;
- Match Report compara solo con 5 partidos anteriores, nunca futuros.

Nueva capa descriptiva:

```text
reports/report_data_access.py
→ agregados raw jugador-partido → equipo-partido
reports/report_metrics.py
→ report_descriptive_v0.1
→ last match / last 5 / previous 5
→ per90 ponderado por minutos para jugador
→ comparación de Match solo contra 5 partidos anteriores
reports/data_builder.py
→ schema 0.6.0
reports/pdf_engine_elite.py
→ renderer REPORTS-03
reports/pdf_engine_es.py
→ wrapper de app apuntando al renderer elite
```

Métricas incorporadas cuando existen:
- precisión de pase;
- remates;
- goles;
- entradas ganadas;
- intercepciones;
- pérdidas;
- desposesiones;
- player per90 para producción individual;
- Match Rating/confianza/dimensiones ya materializados;
- Performance Index complementario;
- motor experto y cobertura.

Pendiente para cerrar REPORTS-03:
1. `py_compile` de la nueva capa;
2. `validate_reports_pro.py` con schema 0.6.0;
3. generar Team / Player / Match;
4. gate visual humano con exigencia de staff profesional;
5. corregir solo problemas demostrados;
6. cerrar y volver a Collector.

## Producto actual

### Home / Centro de mando
Último partido, brief operativo, forma, tendencias, cambios 5-vs-5, ratings, calidad de datos y navegación.

### Jugador
Match Rating V5, confianza, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF profesional.

### Equipo
Match Rating V5, forma, mapa de plantilla, tendencias, participación, Performance Index, historial y PDF profesional.

### Partido
Ratings V5, confianza, roles, minutos, dimensiones, observaciones deterministas y PDF profesional.

### Físico / GPS
Capa opcional descriptiva. La base local no contiene suficientes observaciones GPS reales para una demo completa.

### Alertas
Solo estados auditables de contexto/calidad.

## Collector — siguiente fase tras REPORTS-03

Funcionalmente cerrado; falta producto/UX.

Pendiente:
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
- PDF final = informe técnico profesional independiente, no reproducción literal de la web;
- REPORTS-03 añade solo agregados descriptivos transparentes y versionados.

## Decisiones descartadas / aplazadas

- seguir optimizando indefinidamente qwen3:1.7b: descartado MVP;
- LLM bilingüe CA+ES: descartado MVP, castellano oficial;
- confiar solo en pass rate automático: descartado;
- modificar DuckDB para anonimizar: descartado;
- XI ideal / predicciones / fatiga / lesión sin capa analítica validada: no permitido;
- login SaaS completo, pagos y recuperación de contraseña: aplazado tras el MVP;
- publicación pública del dataset real: bloqueada por derechos/licencia;
- PDF como simple captura de la web: descartado;
- PDF como tabla-resumen mínima: descartado;
- copiar métricas/layouts propietarios de Opta/Wyscout/StatsBomb: descartado.

## Problemas abiertos

- REPORTS-03 gate técnico + visual;
- Collector UX / castellano / móvil;
- demo GPS con datos reales o ejemplo claramente etiquetado;
- autenticación real para producto comercial;
- QA global final;
- documentación final del TFM;
- derechos/licencia antes de despliegue público.

## Siguiente paso exacto

1. ejecutar gate local REPORTS-03 (`py_compile` + `validate_reports_pro.py`);
2. revisar visualmente Team / Player / Match nuevos;
3. cerrar REPORTS-03 si PASS;
4. entrar en **COLLECTOR UX / castellano / móvil**;
5. después demo GPS → QA global → documentación final TFM.
