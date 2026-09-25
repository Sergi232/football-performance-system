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
DECISION POLICY / N13000            GATE C APROBADO — ISSUE #27 CERRADO
DSAI-01A FEASIBILITY AUDIT          CERRADO — ISSUE #28
DSAI-02 CHANGE DETECTION            CERRADO EXPERIMENTAL / NO DEPLOY — ISSUE #29
DSAI-03 PLAYER SIMILARITY           ACTIVO — ISSUE #32
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## 2. Forma de trabajo

Flujo architecture-first + gated. GitHub es la fuente de verdad.

Documentos principales:
1. `PROJECT_STATE.md`;
2. `docs/ARCHITECTURE.md`;
3. `docs/DECISIONS.md`;
4. `docs/WORKFLOW.md`;
5. `docs/DATA_SCIENCE_AI_STRATEGY.md`;
6. `docs/DSAI_EXPERIMENT_PLAN.md`;
7. `README.md`.

## 3. Arquitectura vigente

```text
CAPTURE / IMPORT
→ RAW + NORMALIZED DATA
→ FEATURE ENGINE
→ ANALYTICS ENGINE
→ DECISION ENGINE
→ DS / ML EXPERIMENTAL CORE
→ PRODUCT SERVICE LAYER
→ WEB / REPORTS / AI ASSISTANT
→ QA / PUBLICATION
```

Una capa superior no puede inventar métricas, rankings, evaluaciones o recomendaciones que no existan en una capa inferior validada.

## 4. Prioridad académica

El TFM es de Data Science e IA. El producto web es el vehículo final, pero el núcleo académico debe quedar demostrado en:
- data engineering;
- feature engineering leakage-safe;
- analytics estadístico;
- sistema experto auditable;
- experimentación DS/ML;
- validación y explicabilidad;
- IA generativa como capa final, no como motor de cálculo.

## 5. Baseline de datos

Caso de desarrollo: Deportivo Alavés 2025/26.

```text
matches=38
players=36
player_match=835
```

FEATURE-01 `0.1.0`: 28 features.
FEATURE-02 `0.2.0`: temporal strict-past.
FEATURE-03 `0.3.0`: temporal same-role strict-past.

Roles observados: 590/835 player-match con rol; 23 raw labels.

## 6. ANALYTICS-01 — CERRADO

DG-AN-01 = C:
- `SELF_ROLE_PRIOR`;
- `PEER_ROLE_PRIOR`;
- sempre separats.

Validació:
```text
analytics rows=46760
SELF_ROLE_PRIOR=23380
PEER_ROLE_PRIOR=23380
strict-past peer checks=PASS
FEATURE-03 provenance=PASS
no score/ranking/recommendation=PASS
```

## 7. N13000 policy

DG-N13-01 = C.

Contracte objectiu futur:
- recomanació;
- confiança/calibració;
- evidència;
- justificació;
- limitacions;
- alternativa.

Encara no s’autoritza cap recomanació perquè no hi ha criteris/thresholds/calibració validats. N13000 manté `RECOMMENDATION_NOT_ISSUED_*`.

## 8. DSAI-01A — FEASIBILITY AUDIT CERRADO

Resultat:
```text
player_similarity_profiles        GO_EXPLORATORY
change_detection_evolution        GO_EXPERIMENT
observed_role_classification      CANDIDATE_SUPERVISED
role_player_fit                   REFORMULATE_TARGET
expert_vs_ml                      BLOCKED_SHARED_TARGET
n13000_recommendation_calibration BLOCKED_GROUND_TRUTH
```

Més dades:
```text
player-role sequences=87
repeated=67
median_matches=5
max_matches=38
FEATURE-01 non-null=6324/23380
GPS observations=0
```

## 9. DSAI-02 — CHANGE DETECTION CERRADO EXPERIMENTAL

Script: `dsai/change_detection_experiment.py`.

Estadístic experimental:
```text
abs(current - same_role_prior_mean) / same_role_prior_std
```

Cobertura:
```text
evaluable_rows=3647
players=25
roles=18
features=25
```

Validació sintètica:
```text
0.5 std  AUC=0.2365  median uplift=-0.4645
1.0 std  AUC=0.5341  median uplift= 0.0355
1.5 std  AUC=0.7211  median uplift= 0.5355
2.0 std  AUC=0.8024  median uplift= 1.0355
```

Interpretació:
- mediana natural aproximada ≈ `0.9645σ`;
- 0.5σ queda dins la variació natural;
- 1σ té molt solapament;
- 1.5–2σ ofereixen separació creixent;
- no existeix ground truth real de change-points.

Decisió: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

No s’ha creat threshold operatiu, alerta, ranking ni recomanació.

## 10. DSAI-03 — PLAYER SIMILARITY ACTIU

Issue #32.

Implementat:
```text
dsai/player_similarity_experiment.py
```

Unitat:
```text
player_id + exact observed primary_role
```

Mètode inicial:
- perfil = mitjana de FEATURE-01 en partits jugats dins del mateix rol;
- `Substitute` exclòs de comparacions tàctiques;
- z-standardisation per feature;
- sense imputació de missing values;
- distància RMS sobre features comuns no nuls;
- comparació només entre el mateix rol observat;
- nearest-neighbour exploratori;
- validació temporal primera vs segona meitat;
- escalat temporal ajustat només amb primera meitat.

Guardrails:
- similarity ≠ quality;
- similarity ≠ player fit;
- similarity ≠ recommendation;
- cap score global de rendiment;
- cap target N12000/N13000.

## 11. DSAI-04 — ROLE-LABEL AUDIT PENDENT

Abans de qualsevol classificació supervisada de rol:
- revisar 23 labels;
- tractar `Substitute` com estat no tàctic fins aclarir semàntica;
- no agrupar rols per intuïció.

## 12. Línies bloquejades

- role/player fit: sense target independent;
- Expert vs ML: sense shared target independent;
- N13000 calibration: sense ground truth;
- GPS ML: 0 observacions en dataset actual.

## 13. Producte actual

Dashboard, Reports i Assistant funcionen tècnicament, però continuen com prototip v0.1.

Pendents després del nucli DS/IA:
- Product UX insight-first;
- Reports-02 professionals;
- arquitectura final LLM local/cloud/híbrida;
- Product Service Layer comú;
- publicació final i TFM.

## 14. Decision gates pendents

- `DG-UX-01`;
- `DG-LLM-01`;
- `DG-REP-01`;
- `DG-PUB-01`.

## 15. Siguiente paso exacto

No cal instal·lar res.

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\player_similarity_experiment.py
```

Després A5 revisa cobertura i estabilitat temporal i decideix si la funcionalitat de similitud és defensable o queda només com a experiment exploratori.