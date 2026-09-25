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
DSAI-04 ROLE-LABEL AUDIT            ACTIVO
FINAL-01                            BLOQUEADO HASTA REDISEÑO DE PRODUCTO
```

## Flujo vigente

`DATA → FEATURES → ANALYTICS → EXPERT → DSAI → PRODUCT → LLM → QA/PUBLICATION`

GitHub es la fuente de verdad. Una capa superior no puede inventar métricas, rankings, scores o recomendaciones.

## Baseline

```text
matches=38
players=36
player_match=835
FEATURE-01=28
observed-role rows=590
raw role labels=23
analytics rows=46760
GPS observations=0
```

## DSAI-02 — change detection

Decisión: `EXPERIMENTALLY_USEFUL / NO_DEPLOY`.

## DSAI-03 — player similarity

```text
profiles=64
players=24
roles=22
features=28
profiles_with_neighbour=61
temporal_eligible=22
same_neighbour=5
retention_rate=0.22727272727272727
pair_distance_corr=0.2143880082112036
```

Decisión: `EXPLORATORY_RESULT / NO_DEPLOY` por baja estabilidad temporal.

## DSAI-04 — role-label audit ACTIVO

Objetivo: auditar `primary_role` antes de cualquier clasificador supervisado.

Puntos obligatorios:
- distribución por label;
- jugadores, titularidad y minutos;
- `Substitute` como posible estado no táctico;
- coexistencia del mismo jugador con roles tácticos;
- transiciones temporales;
- sparsity;
- decisión final sobre target raw.

No agrupar labels por intuición.

## Líneas bloqueadas

- role/player fit;
- Expert vs ML;
- N13000 calibration;
- GPS ML;
- role classification hasta cerrar DSAI-04.

## Producto

Dashboard, Reports y Assistant siguen como prototipo v0.1. Después del núcleo DS/IA: Product UX insight-first → Reports-02 → arquitectura LLM final → Product Service Layer → publicación/TFM.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\role_label_audit.py
```

No instalar nada.