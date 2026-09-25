# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## 1. Estado actual

```text
DATA-01/02/03/04                    CERRADO / VALIDADO
COLLECTOR-01 MVP                    CERRADO FUNCIONALMENTE
GPS-01                              CERRADO / VALIDADO
FEATURE-01/02/03                    CERRADO / VALIDADO
EXPERT-01..07 N1000-N13000          BASELINE CERRADO / VALIDADO
LLM-01/02                           PROTOTYPE v0.1 / CONTRATOS PASS
REPORTS-01                          PROTOTYPE v0.1 / CONTRATO PASS
PUBLICATION-01                      CERRADO / VALIDADO TÉCNICAMENTE
DASHBOARD-01                        PROTOTYPE v0.1 / CONTRACT PASS
ARCHITECTURE-01                     CERRADO — ISSUE #25
ANALYTICS-01                        CERRADO / VALIDADO — ISSUE #26
DECISION POLICY / N13000            GATE APROBADO C — ISSUE #27 CERRADO
DSAI-01A FEASIBILITY AUDIT          CERRADO / EJECUTADO
DSAI-02 CHANGE DETECTION            ACTIVO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## 2. Forma de trabajo vigente

El proyecto usa flujo **architecture-first + gated**. GitHub es la memoria técnica definitiva.

Fuente de verdad:
1. `PROJECT_STATE.md` — estado operativo;
2. `docs/ARCHITECTURE.md` — arquitectura vigente;
3. `docs/DECISIONS.md` — decisiones estructurales/gates;
4. `docs/WORKFLOW.md` — agentes, orden y desbloqueos;
5. `docs/DATA_SCIENCE_AI_STRATEGY.md` — prioridad académica DS/IA;
6. `docs/DSAI_EXPERIMENT_PLAN.md` — plan experimental congelado;
7. `README.md` — presentación e instalación.

## 3. Prioridad académica del TFM — Data Science + IA

La aplicación web es el producto final, pero la contribución académica principal debe quedar demostrada en datos, feature engineering, analytics, sistema experto, ML, validación y explicabilidad.

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

No convertir el proyecto en un dashboard con un LLM añadido. Debe existir al menos un bloque experimental DS/IA serio y reproducible.

## 4. Arquitectura vigente

```text
CAPTURE / IMPORT
      ↓
RAW + NORMALIZED DATA
      ↓
FEATURE ENGINE
      ↓
ANALYTICS ENGINE
      ↓
DECISION ENGINE
      ↓
DS / ML EXPERIMENTAL CORE
      ↓
PRODUCT SERVICE LAYER
      ↓
WEB / REPORTS / AI ASSISTANT
      ↓
QA / PUBLICATION
```

Una capa superior no puede inventar métricas, rankings, evaluaciones o recomendaciones que no existan en una capa inferior validada.

## 5. Orden obligatorio de trabajo

```text
ARCHITECTURE-01              CERRADO
        ↓
ANALYTICS-01                 CERRADO / PASS
        ↓
DECISION POLICY / N13000     GATE C APROBADO
        ↓
DSAI-01A FEASIBILITY AUDIT   CERRADO
        ↓
DSAI-02 CHANGE DETECTION     ACTIVO
        ↓
DSAI-03 SIMILARITY/PROFILES
        ↓
DSAI-04 ROLE-LABEL AUDIT
        ↓
REVISIÓN DE BLOQUEADOS
        ↓
PRODUCT UX
        ↓
REPORTS-02 + ASSISTANT ARCHITECTURE
        ↓
FINAL PRODUCT / PUBLICATION / TFM
```

## 6. Estado real del prototipo

Infraestructura reutilizable:
- DuckDB y esquema;
- Collector funcional;
- GPS normalization;
- FEATURE-01/02/03;
- Analytics-01;
- baseline experto N1000-N13000;
- acceso read-only a datos;
- guardrails LLM;
- tooling PDF;
- tooling de anonimización;
- tests existentes.

No definitivo:
- UX Streamlit actual, demasiado orientada a tablas;
- PDF ReportLab actual, prueba técnica y no informe profesional;
- proveedor/arquitectura final del LLM;
- criterios, umbrales y calibración final de N13000;
- Product Service Layer común para web/report/assistant.

## 7. Caso de desarrollo

Deportivo Alavés 2025/26: 38 partidos, 36 jugadores, 835 `player_match`.

Los datos profesionales sirven para desarrollo/validación. No se publicarán raw files originales. La demo anonimizada está técnicamente validada, pero redistribución sigue condicionada a licencia.

## 8. Datos y features cerrados como baseline

DATA-04: 27 raw stats player-match aprobadas. `key_passes` no se aproxima sin fuente verificada.

FEATURE-01 `0.1.0`: 28 features.

FEATURE-02 `0.2.0`: historial strict-past (`history_n`, `prev`, `prior_mean`, `prior_std`, `delta_prev`, `delta_prior_mean`, `prior_slope`).

FEATURE-03 `0.3.0`: historial jugador + rol observado + feature; 590/835 player-match con rol; 23 raw role labels.

El Feature Engine no decide si una métrica es buena/mala.

## 9. ANALYTICS-01 — CERRADO / VALIDADO

Issue #26 cerrado.

DG-AN-01 aprobado: opción C, con evidencias separadas:
- `SELF_ROLE_PRIOR` — jugador vs su historial strict-past en el mismo rol;
- `PEER_ROLE_PRIOR` — jugador vs peers del mismo equipo/rol, strict-past, excluyendo al jugador actual y con equal-player weighting.

Validación final:

```text
ANALYTICS-01 EVIDENCE CONTRACT: PASS
base FEATURE-01 rows: 23380
analytics rows: 46760
SELF_ROLE_PRIOR rows: 23380
PEER_ROLE_PRIOR rows: 23380
peer strict-past samples independently checked: 30
FEATURE-03 self-history provenance: PASS
Peer-role strict-past / current-player exclusion / equal-player weighting: PASS
No score, ranking, recommendation, sample threshold or good/bad label: PASS
```

## 10. Sistema experto baseline y policy N13000

Motor `expert_0.7.0`: 154.475 decisiones; 2.505 N13000.

`DG-N13-01` queda **APROBADO C**.

Objetivo final de N13000 cuando la policy esté validada:
- recomendación;
- confianza/calibración;
- evidencia;
- justificación auditable;
- limitaciones;
- alternativa cuando proceda.

La aprobación del contrato no autoriza a inventar pesos, umbrales ni confianza. Hasta que DS/estadística/literatura validen criterios y calibración, N13000 conserva `RECOMMENDATION_NOT_ISSUED_*`.

## 11. DSAI-01A — FEASIBILITY AUDIT CERRADO

Ejecución local completada:

```text
matches=38
players=36
player_match=835
observed-role rows=590
raw role labels=23
labeled_players=28
player-role sequences=87
repeated=67
median_matches=5.0
max_matches=38
FEATURE-01 names=28
FEATURE-01 non-null=6324/23380
analytics rows=46760
GPS observations=0
```

Resultado por caso:

```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

Interpretación metodológica:
- change detection es el primer experimento por disponer de secuencias repetidas y baseline temporal strict-past;
- similarity/profiles es viable como exploratorio, con validación de estabilidad;
- observed-role classification necesita antes un audit semántico de labels: `Substitute` aparece como etiqueta y no equivale a un rol táctico específico;
- role/player fit no dispone de target externo defendible;
- Expert vs ML queda bloqueado sin shared target independiente;
- N13000 no puede calibrarse sin ground truth de recomendación;
- GPS no entra en experimentos actuales porque hay 0 observaciones.

Plan congelado: `docs/DSAI_EXPERIMENT_PLAN.md`.

## 12. DSAI-02 — CHANGE DETECTION ACTIVO

Implementado:

```text
dsai/change_detection_experiment.py
```

Objetivo: estudiar detección de cambios sobre secuencias `jugador + rol observado + feature` usando referencias FEATURE-03 estrictamente anteriores.

Estadístico experimental:

```text
abs(current - same_role_prior_mean) / same_role_prior_std
```

No es una métrica de producto ni un score de rendimiento. Se usa únicamente para evaluar sensibilidad.

Validación inicial:
- inyección sintética del valor actual a 0.5 / 1.0 / 1.5 / 2.0 desviaciones estándar del prior;
- el baseline strict-past no se modifica;
- ROC-AUC experimental original vs injected;
- cobertura y sensibilidad por longitud de historial;
- sin seleccionar threshold operativo;
- sin etiqueta bueno/malo;
- sin recomendación.

Outputs locales:

```text
dsai/output/change_detection_experiment.json
dsai/output/change_detection_experiment.md
```

## 13. Próximos experimentos

### DSAI-03 — Player similarity / profiles
Segundo experimento. Perfil agregado jugador-rol con FEATURE-01, distancias simples como baseline y validación de estabilidad. No equivaldrá a ranking de calidad.

### DSAI-04 — Role-label audit
Antes de cualquier clasificador supervisado se debe revisar la semántica de `primary_role`, distribución de clases y el uso de `Substitute`. No se agruparán etiquetas por intuición.

### Líneas bloqueadas
- role/player fit: reformular target;
- Expert vs ML: requiere shared target independiente;
- N13000 calibration: requiere ground truth.

## 14. Prototipos de producto

### Dashboard
Contract PASS. TEAM / PLAYER / MATCH / ASSISTANT funcionan técnicamente, pero predominan tablas y faltan insights estructurados.

### Reports
REPORTS-01 PASS. Los tres PDF se generan, pero son prueba técnica y no informes finales entregables.

### Assistant
LLM-01/02 PASS en contratos y guardrails. Decisión final local/cloud/híbrida pendiente. La IA generativa es capa de interacción, no el núcleo científico del TFM.

## 15. Agents / ownership

Definidos en `docs/WORKFLOW.md`:
- A0 Architect/Integrator;
- A1 Data & Collector;
- A2 Feature Engine;
- A3 Analytics;
- A4 Expert/Decision Engine;
- A5 ML/Validation;
- A6 Product/UX;
- A7 Reporting;
- A8 AI Assistant;
- A9 QA/Publication.

A5 es ahora el agente principal. A0 y A9 acompañan la fase.

## 16. Decision gates

Registro: `docs/DECISIONS.md`.

- `DG-AN-01` — **APPROVED C**;
- `DG-N13-01` — **APPROVED C**;
- `DG-UX-01` — pendiente;
- `DG-LLM-01` — pendiente;
- `DG-REP-01` — pendiente;
- `DG-PUB-01` — pendiente/derechos.

No hay gate de Sergi necesario para ejecutar DSAI-02.

## 17. Restricciones vigentes

- no inventar eventos atómicos desde agregados ambiguos;
- no inferir rol/formación sin evidencia;
- no crear scores/umbrales de producto por intuición;
- no mezclar self-history y peer comparison silenciosamente;
- no usar LLM para cálculo crítico;
- no emitir recomendación N13000 sin criterios/calibración validados;
- no crear targets ML circulares a partir del propio sistema experto;
- no publicar datos profesionales solo por estar anonimizados;
- no usar `Substitute` como rol táctico sin resolver su semántica;
- no rediseñar web/report/assistant antes del núcleo DS/IA prioritario.

## 18. Siguiente paso exacto

Ejecutar DSAI-02, sin instalar nada:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\change_detection_experiment.py
```

Después, A5 revisará cobertura, sensibilidad y limitaciones y decidirá si DSAI-02 pasa a una segunda validación o se cierra como evidencia experimental antes de DSAI-03.