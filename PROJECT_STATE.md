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
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01                              PROTOTYPE v0.1 / CONTRATOS PASS
LLM-02 LOCAL COACH COPILOT          CERRADO MVP / CASTELLANO / LIMITACIÓN MENOR DOCUMENTADA
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
REPORTS-02 PROFESSIONAL PDF         BASELINE CERRADO / GATE TÉCNICO + VISUAL PASS
REPORTS-03 ELITE TECHNICAL REPORTS  CERRADO / V6 / GPS INTEGRADO / GATE PASS
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

## Hipótesis principal del TFM

Formulación actual:

> **Un equipo de fútbol amateur o semiprofesional puede disponer de un sistema integral y auditable de soporte a la decisión a partir de datos de vídeo y GPS opcional, capaz de transformarlos en información sobre rendimiento, evolución, rol y comportamiento físico de los jugadores y del equipo.**

### Estado de contraste

La hipótesis está **contrastada favorablemente en su dimensión técnica y arquitectónica** mediante un prototipo funcional end-to-end.

Evidencia ya disponible:
- temporada completa de demostración: 38 partidos y 590 apariciones jugador-partido;
- Data Collector V1.1 cerrado y compatible con la taxonomía aprobada;
- Data Layer DuckDB con unidad principal jugador-partido;
- Feature Engine determinista y temporalmente seguro;
- Match Rating V5 operativo desde el primer partido;
- Performance Index histórico/posicional separado del Match Rating;
- sistema experto jerárquico y auditable N1000-N13000;
- Team / Player / Match Mode operativos;
- GPS opcional integrado mediante capa canónica normalizada;
- dashboard profesional;
- Coach Copilot local downstream de analytics;
- PDF Team / Player / Match V6 con contexto GPS descriptivo;
- anonimización de presentación, control de acceso y gates de seguridad.

Lo que **NO** está demostrado y no debe afirmarse en la memoria:
- que el sistema mejore objetivamente las decisiones de un entrenador;
- que aumente el rendimiento deportivo del equipo;
- que el GPS sintético valide fisiología real;
- fatiga, readiness/disponibilidad física o riesgo de lesión;
- capacidad predictiva clínica o preventiva;
- impacto comercial real sin validación de mercado.

La validación con entrenadores/analistas reales sería una mejora fuerte, pero **no puede inventarse ni simularse como evidencia empírica**. Si se realiza, debe ser con participantes reales y metodología documentada.

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

Collector V1.1 actual:
- identificación: jugador, dorsal editable, titular/suplente explícito, minutos;
- contexto de partido: partido, equipo, rival, fecha, formación;
- pase: completada, no completada, pase clave, asistencia;
- progresión: centro, pase largo;
- 1v1: regate completado, pérdida;
- finalización: remate, remate a puerta, bloqueado, gol;
- defensa: entrada, intercepción, bloqueo, despeje;
- disciplina: falta cometida, falta recibida, tarjeta, penal;
- portero: parada, gol encajado;
- contexto jugador: rol/posición, lado y cambio de posición;
- equipo/ABP: córners a favor/en contra y resultado posterior de la secuencia;
- faltas con localización x/y para derivar posteriormente peligrosidad con regla validada.

Reglas clave:
- `SHOT GOAL` y `SHOT ON_TARGET` cuentan en el agregado derivado `A puerta`;
- una pasada `LONG` o `CROSS` ya cuenta en pase total;
- `PASS FAIL` y `DRIBBLE FAIL` generan pérdidas derivadas;
- no existe botón subjetivo `falta_peligrosa`;
- no se registran manualmente métricas avanzadas derivables.

GPS es opcional y se normaliza a esquema común.

## COLLECTOR-01 — CERRADO V1.1

Implementación oficial:

```text
collector/data_collector_futbol.html
→ collector/data_collector_futbol_v1.html
```

Taxonomía vigente:

```text
event_catalog v0.3.0
```

Commit de implementación final validada: `802173d` — `Finalize Collector V1.1`.

Cierre confirmado localmente:

```text
COLLECTOR V1.1 FINAL GATE: PASS
catalog_version=0.3.0
structured_opponent=PASS
editable_shirt_number=PASS
starter_substitute_explicit=PASS
starter_minutes_consistency_guard=PASS
shots_on_target_goal_plus_on_target=PASS
spanish_visible_labels=PASS
responsive_metadata_access=PASS
mobile_touch_targets=PASS
dynamic_form_ids_names_labels=PASS
summary_interactive_element_guard=PASS
event_taxonomy_unchanged=PASS
official_entrypoint=PASS
4 collector contract tests: PASS
COLLECTOR-01 IMPLEMENTACION FINAL: PASS
```

V1.1 incorpora y preserva:
- UI visible en castellano;
- dorsal editable;
- titular/suplente explícito y coherente con minutos iniciales;
- rival estructurado como `opponentName`;
- metadatos accesibles en responsive;
- targets táctiles adecuados;
- autosave, undo, CSV eventos, CSV resumen y JSON;
- captura x/y de faltas;
- flujo de ABP;
- cambios de rol/formación;
- `id`, `name` y labels asociados en campos dinámicos;
- eliminación de control interactivo dentro de `<summary>`.

La validación responsive es estructural/contractual; no se presenta como estudio de usabilidad con usuarios reales ni como certificación de todos los dispositivos físicos.

Documentación:
- `collector/COLLECTOR_MVP.md`;
- `collector/COLLECTOR_UX_AUDIT.md`;
- `collector/validate_collector_v1.py`;
- `tests/test_collector_contract.py`.

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
→ reports/data_builder.py
→ PDF Team / Player / Match V6
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
- correlación minutos-distancia: 0.9225;
- rango distancia respecto al prior rol+minutos: 0.840..1.148;
- duplicados de muestras: 0;
- duplicados de resúmenes latest: 0;
- procedencia sintética explícita: PASS.

Familias físicas demo: `GK`, `CB`, `FB`, `CM`, `AM_W`, `ST`, `OTHER`.

Cobertura posicional:
- 482/590 apariciones (81.7%) tienen rol resoluble desde `primary_role` o `default_position`;
- 108/590 (18.3%) no tienen posición recuperable: `primary_role` y `default_position` indican `Substitute`;
- esas 108 apariciones permanecen en `OTHER` y usan prior genérico de demo;
- no se les asigna una posición específica inventada ni se interpreta su valor como comparación posicional.

Precedencia de fuentes cerrada y validada:

```text
GPS REAL / proveedor observado
→ siempre prioridad sobre GPS sintético para el mismo jugador-partido
→ imported_at solo desempata dentro de la misma clase de fuente
```

`gps/validate_physical_summary.py` incluye fixture explícito con GPS real antiguo + sintético más reciente y exige que el real quede seleccionado.

No se han introducido umbrales de HSR, sprint, workload, fatiga, readiness/disponibilidad física o riesgo de lesión.

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
COLLECTOR V1.1 FINAL GATE: PASS
4 collector contract tests: PASS

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
source_precedence=REAL_OVER_SYNTHETIC
duplicate_samples=0
duplicate_latest_summaries=0

GPS SYNTHETIC COHERENCE AUDIT: PASS
scope=INTERNAL_DEMO_COHERENCE_NOT_PHYSIOLOGICAL_VALIDATION
minutes_conditioning=PASS
role_conditioning=PASS
synthetic_provenance=PASS

GPS PHYSICAL SUMMARY CONTRACT: PASS
summary_version=gps_physical_summary_v0.1-descriptive
source_precedence_fixture=REAL_OVER_SYNTHETIC:PASS
db_gps_observations=38197
db_summary_rows=590
db_latest_rows=590

REPORTS ELITE TECHNICAL GATE V6: PASS
schema=0.7.0
report_metrics=report_descriptive_v0.2
gps_summary=gps_physical_summary_v0.1-descriptive
spanish=PASS
anonymization=PASS
technical_context=PASS
team_last10_all_context=PASS
physical_gps_context=PASS
synthetic_demo_label=PASS
minutes_role_context=PASS
gps_latest_match_alignment=PASS
gps_role_localization=PASS
unsupported_physical_claims_guard=PASS
materialized_match_summary=PASS
critical_recalculation_guard=PASS

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

La página Físico/GPS etiqueta explícitamente `DATOS DEMO · GPS sintético` cuando corresponde y no presenta la demo como observación real.

## ACCESS-CONTROL-01

```text
SUPERADMIN  → todos los equipos
CLUB_ADMIN  → equipos autorizados del club
STAFF       → equipos asignados
```

La capa de datos filtra equipos autorizados y bloquea consultas directas a `team_id` ajenos. Un usuario restringido sin asignaciones falla cerrado.

Autenticación real email/contraseña/sesiones NO implementada todavía. Está separada de autorización y documentada en `docs/ACCESS_CONTROL.md`.

La base demo actual contiene un solo equipo, por lo que el contrato multi-equipo se valida estructuralmente, no mediante una demo visual con varios clubes.

## REPORTS-03 — ELITE TECHNICAL REPORTS — CERRADO V6

Los informes son técnicos para el cuerpo técnico; no son una captura literal de la web.

Capa activa:

```text
reports/report_data_access.py
→ agregados raw jugador-partido → equipo-partido
reports/report_metrics.py
→ report_descriptive_v0.2
reports/data_builder.py
→ schema 0.7.0 + contexto GPS read-only
reports/pdf_engine_elite_v6.py
→ renderer activo Team / Player / Match
reports/pdf_engine_es.py
→ wrapper usado por la app
reports/validate_reports_pro.py
→ gate V6
```

Principios cerrados:
- cambio temporal antes que ranking;
- métricas transparentes junto al Match Rating;
- deltas descriptivos sin etiquetar automáticamente bueno/malo;
- no inventar xG, posesión, pressures, pass networks, heatmaps o tracking sin datos válidos;
- Match Report compara solo con historia anterior, nunca futura;
- el PDF no recalcula Match Rating, Performance Index ni decisiones expertas;
- GPS es descriptivo, downstream y opcional;
- GPS sintético se etiqueta explícitamente como `DATOS DEMO`;
- el rol contextual GPS no sustituye el rol analítico del Match Rating;
- ninguna métrica GPS emite claims de fatiga, disponibilidad física, lesión o calidad del jugador.

V6 conserva el pulso Team `Último / Últimos 10 / Todos / Δ 10 vs todos`, añade GPS descriptivo a los tres informes y `Claves para la revisión física` deterministas.

Validación final local:
- Team PDF: 4 páginas;
- Player PDF: 3 páginas;
- Match PDF: 3 páginas;
- gate técnico V6: PASS;
- revisión visual realizada sin clipping, solapamientos graves ni tablas fuera de página.

## Producto actual

### Home / Centro de mando
Último partido, brief operativo, forma, tendencias, cambios, ratings, calidad de datos y navegación.

### Jugador
Match Rating V5, confianza, perfil, Performance Index, dimensiones, evolución, técnico, motor experto, partidos, GPS descriptivo y PDF V6.

### Equipo
Match Rating V5, forma, mapa de plantilla, tendencias, participación, Performance Index, historial, GPS descriptivo y PDF V6.

### Partido
Ratings V5, confianza, roles, minutos, dimensiones, observaciones deterministas, GPS descriptivo y PDF V6.

### Físico / GPS
Capa opcional descriptiva operativa. Demo sintética canónica disponible, explícitamente etiquetada como no observada y subordinada a GPS real.

### Collector
V1.1 oficial. Captura manual rápida de eventos observables y contexto, en castellano y con layout responsive, sin alterar la taxonomía `event_catalog v0.3.0`.

### Alertas
Solo estados auditables de contexto/calidad.

## Prioridad académica actual

El proyecto ya tiene suficiente profundidad técnica. A partir de este punto, el valor marginal más alto está en **QA global, cierre documental y reproducibilidad** antes que añadir módulos nuevos.

Orden recomendado para maximizar calidad del TFM:
1. QA/regresión global end-to-end del producto;
2. memoria: problema, hipótesis, metodología, arquitectura, experimentos, resultados, limitaciones y conclusiones;
3. documentación reproducible de instalación/demo;
4. validación con entrenadores/analistas reales si es viable, sin inventar participantes ni resultados;
5. preparar defensa y demo final;
6. Power BI o validación comercial solo como complementos opcionales si queda margen.

## Extensiones futuras / opcionales

### Power BI

Puede añadirse como **capa alternativa de consumo**, no como sustituto ni duplicado de la web.

Objetivo defendible:
- demostrar que la capa analítica es independiente del front-end;
- reutilizar el mismo modelo de datos para Team / Player / Match / GPS;
- ofrecer una opción útil para cuerpos técnicos que ya trabajen con el ecosistema Microsoft.

No es requisito para cerrar el TFM ni debe retrasar el producto principal.

### Validación comercial / go-to-market

Puede incorporarse como apartado complementario de viabilidad empresarial:
- target: clubes amateur/semi-profesionales sin departamento de análisis;
- propuesta de valor;
- competidores y alternativas;
- modelo de pricing hipotético;
- coste de implantación;
- piloto y canal de captación.

El scraping de contactos o emailing no forma parte del núcleo DS/IA del TFM. Si se realiza posteriormente, debe respetar protección de datos, términos de uso y normativa aplicable. No presentar contactos inventados ni validación comercial simulada.

### Automatización futura del Data Collector

Extensión estratégica prioritaria a medio plazo:
- visión por computador y análisis automático de vídeo;
- automatización parcial de eventos actualmente manuales;
- reducción de tiempo y coste de captura;
- aumento del volumen/frecuencia de datos disponibles;
- mantenimiento del mismo pipeline analítico downstream.

No se considera implementada ni validada actualmente.

### Datos antropométricos y contexto médico

Edad, altura o peso pueden estudiarse como contexto adicional si existe fuente fiable y justificación analítica.

Un módulo médico/lesiones queda como extensión futura y requeriría:
- datos reales y autorizados;
- gobernanza y control de acceso reforzados;
- separación clara entre información deportiva y sanitaria;
- validación específica antes de cualquier alerta clínica.

No implementar ni afirmar prevención de lesiones, readiness o riesgo individual sin evidencia suficiente.

## Experimentos / decisiones relevantes

- Collector V1.1 cerrado sin modificar `event_catalog v0.3.0`;
- Match Rating V5 validado y congelado;
- Performance Index separado del Match Rating;
- sistema experto jerárquico preferido frente a un único `DecisionTreeClassifier`;
- LLM downstream y sin acceso directo a DB;
- demo anonimizada solo en presentación, no en base de datos;
- control de acceso separado de autenticación;
- PDFs consumen analytics materializados y no recalculan métricas críticas;
- GPS real y GPS demo comparten la capa canónica normalizada;
- GPS real tiene precedencia sobre demo sintética para un mismo jugador-partido;
- demo GPS sintética condicionada por minutos y rol cuando el rol está disponible;
- no inferir una posición de partido cuando la fuente solo informa `Substitute`;
- rol contextual GPS y rol analítico Match Rating son contratos distintos;
- GPS sintético no alimenta Match Rating, Performance Index ni decisiones expertas;
- PDF final = informe técnico profesional independiente, no reproducción literal de la web;
- la hipótesis principal se plantea como viabilidad técnica/auditable, no como prueba de mejora causal de decisiones deportivas.

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
- copiar métricas/layouts propietarios de Opta/Wyscout/StatsBomb: descartado;
- inventar validación con entrenadores, clientes o usuarios: no permitido.

## Problemas abiertos

- QA global final end-to-end del producto;
- documentación final del TFM y README de entrega;
- defensa/demo final;
- validación con usuarios reales si es viable;
- autenticación real para producto comercial;
- derechos/licencia antes de despliegue público;
- validación futura con GPS real si se dispone de un proveedor/dataset autorizado.

## Siguiente paso exacto

1. ejecutar QA/regresión global end-to-end: Collector/import → DuckDB → Feature Engine → analytics → sistema experto → dashboard → asistente → PDF;
2. verificar contratos, compatibilidad de esquemas, ausencia de recalculaciones críticas y funcionamiento sin GPS;
3. registrar incidencias reales del QA y corregir solo fallos concretos, sin reabrir módulos ya cerrados por preferencia estética;
4. cerrar documentación final (`README.md`, arquitectura, instalación, demo, hipótesis, metodología, resultados y limitaciones);
5. preparar la defensa del TFM;
6. solo si queda margen, añadir Power BI, validación con entrenadores reales o sección comercial como complementos opcionales.
