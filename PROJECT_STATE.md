# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## Estado actual

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
DECISION POLICY / N13000            GATE APROBADO — ISSUE #27 CERRADO
DSAI-01A FEASIBILITY AUDIT          CERRADO — ISSUE #28
DSAI-02 CHANGE DETECTION            CERRADO EXPERIMENTAL / NO DEPLOY — ISSUE #29
DSAI-03 PLAYER SIMILARITY           CERRADO EXPLORATORIO / NO DEPLOY — ISSUE #32
DSAI-04 ROLE-LABEL AUDIT            CERRADO / REFORMULATE_LABELS — ISSUE #34
DSAI-05 ROLE TARGET RECONSTRUCTION  ACTIVO — ISSUE #35 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-04 — resultado cerrado

```text
labeled_rows=590
raw_labels=23
labeled_players=28
Substitute rows=172
Substitute players=23
players_also_with_tactical_role=19
conclusion=RAW_TARGET_REQUIRES_SOURCE_BASED_CLEANING_BEFORE_SUPERVISED_MODELLING
```

Decisión: `REFORMULATE_LABELS`.

`Substitute` es un estado de participación y no una clase táctica. No se entrena ningún clasificador sobre los 23 labels brutos.

## DSAI-05 — activo

Issue #35.

Script: `dsai/role_target_reconstruction.py`.

Objetivo:
- separar `participation_status` de `tactical_role`;
- conservar únicamente roles tácticos directamente observados;
- dejar sin rol táctico los suplentes cuando la fuente no lo proporciona;
- no imputar por historial, posición habitual ni intuición;
- cuantificar cobertura, clases y dependencia por jugador antes de decidir si procede ML supervisado.

La reconstrucción no modifica la base normalizada y genera CSV/JSON/Markdown reproducibles.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_target_reconstruction.py
```

No instalar nada.
