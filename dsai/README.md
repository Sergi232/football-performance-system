# DSAI — Data Science / AI experimental core

Fecha de sincronización: 03/10/2026

Esta carpeta contiene la fase experimental de Data Science / IA del TFM.

Regla general: un resultado `NO_DEPLOY` es válido si el experimento está bien formulado, leakage-safe, comparado contra baselines adecuados y documentado.

## DSAI-01A — feasibility audit — CERRADO

El audit local confirmó una base suficiente para experimentación, con temporada completa demo, jugadores, `player_match`, roles observados y features materializadas.

## DSAI-02 — change detection / evolution — CERRADO

Resultado:

```text
EXPERIMENTALLY_USEFUL / NO_DEPLOY
```

Existe señal descriptiva útil, pero no un threshold de producto defendible.

## DSAI-03 — player similarity / profiles — CERRADO

Resultado:

```text
EXPLORATORY_RESULT / NO_DEPLOY
```

Motivo principal: estabilidad temporal insuficiente para producto.

## DSAI-04 — role-label audit — CERRADO

Resultado:

```text
REFORMULATE_LABELS
```

`Substitute` mezclaba estado de participación y rol táctico.

## DSAI-05 — role target reconstruction — CERRADO

Se reconstruyó un target táctico limpio y se excluyó `Substitute` del target de posición. No se infiere rol de suplentes sin evidencia observada.

## DSAI-06 — supervised role feasibility — CERRADO

Resultado:

```text
LIMITED_EXPERIMENT_ONLY
```

## DSAI-07 — detailed-role baseline — CERRADO

Resultado:

```text
EXPERIMENTAL_SIGNAL / NO_DEPLOY
```

La granularidad de rol detallado mostró señal insuficiente para producto.

## DSAI-08 — source-position granularity audit — CERRADO

Se redujo la representación a `source_position` a partir de la estructura validada de DATA-02, sin introducir labels nuevos por conveniencia.

Resultado:

```text
LIMITED_SOURCE_POSITION_BASELINE
```

## DSAI-09 — source-position current-match baseline — CERRADO

Resultado:

```text
EXPERIMENTAL_SIGNAL_IMPROVED / NO_DEPLOY
```

FEATURE-01 del mismo partido contiene señal sobre la posición observada, pero el experimento es post-partido y no constituye una solución pre-match.

## DSAI-10 — pre-match source-position baseline — CERRADO

Se restringieron inputs a FEATURE-02 strict-past (`history_n`, `prev`, `prior_mean`, `prior_std`, `prior_slope`).

Quedaron excluidos:
- `delta_prev`;
- `delta_prior_mean`;
- FEATURE-01 del partido actual;
- FEATURE-03 actual.

Resultado:

```text
PREMATCH_EXPERIMENTAL_SIGNAL / NO_DEPLOY
```

## DSAI-11 — pre-match robustness and football baselines — CERRADO

Script:

```powershell
python dsai\source_position_prematch_robustness.py
```

Objetivo: comprobar si DSAI-10 aporta valor incremental frente a baselines futbolísticos simples disponibles antes del partido.

Comparaciones:
- modelo completo con FEATURE-02 pre-match seguras;
- `prior_mean_only`;
- `prev_only`;
- mayoría del train;
- última `source_position` observada del jugador;
- posición modal histórica del jugador.

Reglas metodológicas:
- solo información estrictamente anterior;
- jugador evaluado excluido del train de esa fila;
- ningún input del partido actual;
- análisis role-stay vs role-switch;
- head-to-head ML vs última posición.

Resultado final: **los baselines simples de historial posicional, especialmente la última posición observada, superan claramente al modelo ML pre-match en esta muestra**.

Decisión:

```text
POSITION / ROLE ML
= CONTEXT ONLY
= NO DEPLOY
```

Interpretación académica: no se fuerza ML cuando una regla simple, auditable y disponible pre-match funciona mejor.

## Líneas bloqueadas

### role_player_fit

Sin ground truth independiente defendible.

```text
REFORMULATE_TARGET / NO DEPLOY
```

### expert_vs_ml

No existe todavía un target externo común que permita comparar Expert System y ML de forma independiente.

```text
BLOCKED_SHARED_TARGET
```

### calibración final N13000

No existen outcomes/labels externos suficientes para convertir confidence interna en probabilidad calibrada de recomendación correcta.

```text
BLOCKED_GROUND_TRUTH
```

## Relación con el producto final

Ningún modelo experimental de esta carpeta sustituye:
- Match Rating V5;
- Performance Index;
- Analytics;
- N1000-N13000.

Los experimentos DS/ML aportan evidencia metodológica, incluyendo resultados negativos y decisiones de no-deploy.

## Regla metodológica

Toda fase DSAI debe documentar:
- hipótesis;
- datos y target;
- baseline simple;
- control de leakage;
- split/validación;
- métricas;
- análisis de error/estabilidad;
- limitaciones;
- decisión deploy/no-deploy.

No desplegar es un resultado válido cuando la evidencia no supera un baseline simple o no existe un constructo suficientemente defendible.
