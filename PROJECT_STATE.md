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
DSAI-05 ROLE TARGET RECONSTRUCTION  CERRADO / VALIDADO — ISSUE #35
DSAI-06 SUPERVISED ROLE FEASIBILITY ACTIVO — ISSUE #36 / SCRIPT IMPLEMENTADO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## DSAI-05 — resultado cerrado

```text
rows=835
played=590
starters=418
substitute_appearances=172
unused_bench=245
clean_target_rows=418
labels=22
players=24
single_player_labels=3
withheld_substitute_appearances=172
invalid_starter_rows=0
substitute_labels_remaining=0
conclusion=CLEAN_TARGET_RECONSTRUCTED_SUPERVISED_FEASIBILITY_STILL_REQUIRED
```

Decisión: target táctico semánticamente limpio y validado. `Substitute` queda separado como estado de participación y no existe en el target táctico. No se infiere ningún rol para suplentes.

## DSAI-06 — activo

Issue #36.

Script: `dsai/role_supervised_feasibility.py`.

Objetivo: determinar si las 418 observaciones, 22 clases y 24 jugadores permiten un experimento supervisado defendible sin memorizar identidad.

Audita:
- cobertura de FEATURE-01 en las filas del target limpio;
- soporte de cada clase por jugadores y partidos;
- elegibilidad temporal strict-past;
- soporte strict-past del mismo label en otro jugador;
- clases de un único jugador;
- diseño de validación leakage-safe.

Guardrails:
- no entrena ningún modelo;
- no fusiona ni elimina clases por conveniencia;
- `player_id`, nombres, `primary_role`, FEATURE-03 y outputs N12000/N13000 no pueden ser predictores;
- no introduce mínimos de muestra arbitrarios.

Salida posible: `GO_BASELINE_EXPERIMENT`, `LIMITED_EXPERIMENT_ONLY` o `NO_GO_SUPERVISED`.

## Líneas todavía bloqueadas

- `role_player_fit`: sin target independiente defendible;
- `expert_vs_ml`: sin shared target independiente;
- calibración N13000: sin ground truth de recomendación.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_supervised_feasibility.py
```

No instalar nada.
