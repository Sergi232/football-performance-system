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
REPORTS-02 PROFESSIONAL PDF         CERRADO VISUALMENTE / ES + DEMO ANONIMIZADA
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

La web es el producto principal. Los PDF son exportaciones estáticas complementarias.

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

REPORTS-02 PDF CONTRACT: PASS
schema=0.4.1
language_es=PASS
anonymization=PASS
real_identity_leak_payload=0
guardrails=PASS
Team / Player / Match generados

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

## REPORTS-02 — CERRADO

Arquitectura:

```text
analytics materializados
→ reports/data_builder.py
→ anonimización final de payload
→ reports/pdf_engine_es.py
→ PDF Team / Player / Match
```

Estado final:

- schema `0.4.1`;
- castellano;
- anonimizados antes del render;
- Team: 2 páginas útiles;
- Player: 1 página;
- Match: 1 página;
- fechas limpias;
- roles y perfiles traducidos;
- códigos internos sustituidos por etiquetas legibles;
- cobertura experta formateada en porcentaje;
- estado experto traducido;
- sin nombres reales detectados en payload demo;
- gate visual humano PASS;
- `Exportar PDF` reactivado en Equipo, Jugador y Partido mediante `reports/pdf_engine_es.py`.

Ficheros clave:

- `reports/data_builder.py`
- `reports/pdf_engine_es.py`
- `reports/validate_reports_es.py`
- `app/pages/2_Jugador.py`
- `app/pages/3_Equip.py`
- `app/pages/4_Partit.py`

## Producto actual

### Home / Centro de mando
Último partido, brief operativo, forma, tendencias, cambios 5-vs-5, ratings, calidad de datos y navegación.

### Jugador
Match Rating V5, confianza, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos y PDF.

### Equipo
Match Rating V5, forma, mapa de plantilla, tendencias, participación, Performance Index, historial y PDF.

### Partido
Ratings V5, confianza, roles, minutos, dimensiones, observaciones deterministas y PDF.

### Físico / GPS
Capa opcional descriptiva. La base local no contiene suficientes observaciones GPS reales para una demo completa.

### Alertas
Solo estados auditables de contexto/calidad.

## Collector — siguiente fase activa

Funcionalmente cerrado; ahora toca producto/UX.

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
- PDFs consumen analytics materializados y no recalculan métricas críticas.

## Decisiones descartadas / aplazadas

- seguir optimizando indefinidamente qwen3:1.7b: descartado MVP;
- LLM bilingüe CA+ES: descartado MVP, castellano oficial;
- confiar solo en pass rate automático: descartado;
- modificar DuckDB para anonimizar: descartado;
- XI ideal / predicciones / fatiga / lesión sin capa analítica validada: no permitido;
- login SaaS completo, pagos y recuperación de contraseña: aplazado tras el MVP;
- publicación pública del dataset real: bloqueada por derechos/licencia.

## Problemas abiertos

- smoke test local tras reactivar exportación PDF en las tres páginas;
- Collector UX / castellano / móvil;
- demo GPS con datos reales o ejemplo claramente etiquetado;
- autenticación real para producto comercial;
- QA global final;
- documentación final del TFM;
- derechos/licencia antes de despliegue público.

## Siguiente paso exacto

1. `git pull` y `py_compile` de `2_Jugador.py`, `3_Equip.py`, `4_Partit.py`;
2. abrir Streamlit y confirmar que `Exportar PDF` aparece en Equipo / Jugador / Partido en `FPS_DEMO_MODE=1`;
3. si PASS, no volver a tocar REPORTS-02;
4. entrar en **COLLECTOR UX / castellano / móvil**;
5. después demo GPS → QA global → documentación final TFM.
