# Match Rating — product contract

Fecha de sincronización: 03/10/2026

## Purpose

`Match Rating` es la evaluación inmediata jugador-partido expuesta al cuerpo técnico después de un partido. Está deliberadamente separada del `Performance Index` histórico.

## Versión vigente

```text
Match Rating: match_rating_v0.5-candidate
Performance Index: performance_score_v0.2-experimental
```

Match Rating V5 es el baseline activo y congelado. No se modifica fórmula, pesos o arquitectura sin nueva evidencia, experimento explícito y validación.

## Operational requirement

Después del primer partido procesado de un club, todo jugador con `minutes_played > 0` debe tener:

- Match Rating en escala `/10`;
- valor de confianza/evidencia;
- contexto/status transparente;
- datos observados jugador-partido disponibles para explicación;
- inclusión en Match Mode e informe de partido.

No se requiere historial previo del club.

Contrato validado actual:

```text
played_rows=590
rated_rows=590
rating_coverage=1.0000
matches=38
goalkeeper_rows=38
generic_role_rows=172
neutral_insufficient_evidence_rows=0
first_match_rated_rows=16
MATCH RATING CONTRACT: PASS
```

Control de integridad del baseline:

```text
nulls=0
duplicates=0
out_of_range=0
```

## Outfield model

El modelo de jugadores de campo usa contexto posicional cuando existe rol fiable.

Familias principales:

```text
CB / FB / DM / CM / AM / W / ST
```

La ruta activa validada es `OUTFIELD_PERF18_ANCHORED` cuando existe evidencia suficiente y rol resoluble.

Los anchors decisivos son explícitos y auditables. No se introduce un castigo global automático por resultado del equipo.

## Goalkeepers

Los porteros siguen una ruta separada y nunca se evalúan mediante las dimensiones posicionales de jugadores de campo.

Baseline vigente:

```text
90% shot-stopping
10% distribución
```

Las 38 apariciones de portero de la temporada demo están cubiertas por esta ruta específica.

## Missing role / generic route

Si una fuente externa solo etiqueta una aparición jugada como `Substitute` y no existe rol táctico fiable, el sistema puede usar una ruta genérica de rating.

Debe cumplir:
- no inventar posición;
- conservar al jugador visible;
- exponer el contexto/ruta usada;
- mantener confidence/provenance.

La temporada demo actual contiene 172 apariciones evaluadas mediante esta ruta genérica por falta de rol fiable.

El Collector first-party V1.1 registra rol/posición y cambios de rol para reducir esta limitación en datos propios.

## Historical layer

`Performance Index` es complementario y puede usar historia/contexto de rol para:
- evolución;
- forma;
- consistencia;
- perfil de rol;
- tendencias descriptivas.

No debe presentarse como Match Rating jugador-partido.

## Missing evidence

La ausencia de evidencia nunca se convierte silenciosamente en cero observado.

Cuando una señal no está disponible:
- se preserva `NULL`/ausencia cuando corresponde;
- no se inventan acciones;
- se conserva provenance y confidence;
- la interfaz debe explicar la limitación.

## LLM boundary

El Coach Copilot está downstream del Match Rating materializado.

Puede:
- consultar el rating;
- explicar la evidencia disponible;
- describir evolución/comparaciones permitidas.

No puede:
- recalcularlo;
- alterar pesos;
- sustituir la ruta V5;
- convertirlo automáticamente en una recomendación táctica.

## GPS boundary

GPS es opcional y no modifica el Match Rating V5.

En particular, GPS sintético de demo nunca alimenta el rating.

## Interpretation boundary

La escala `/10` es una escala propia del producto y no se presenta como equivalente a un rating propietario externo.

Las referencias profesionales usadas durante el desarrollo sirven para normalización/validación experimental, no como dependencia necesaria del producto amateur ni como promesa de equivalencia con proveedores externos.
