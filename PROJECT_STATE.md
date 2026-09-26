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
DSAI-01A..11                        CERRADO / RESULTADOS DOCUMENTADOS
PERF-01..13                         CERRADO / SCORE POLICY VALIDADA
PERF-14 POSITION-SPECIFIC SCORE     CERRADO — ISSUE #87
SCORE-INTEGRATION-01                CERRADO / MATERIALIZACIÓN + CONTRACT PASS
DASHBOARD-02                        ACTIVO — ISSUE #88 / PLAYER VIEW IMPLEMENTADA
FINAL-01                            DESBLOQUEADO
```

## Objetivo principal confirmado

Producto web funcional para cuerpo técnico de fútbol amateur/semiprofesional:

```text
COLLECTOR + GPS opcional
-> DATABASE
-> FEATURE ENGINE
-> ANALYTICS
-> EXPERT SYSTEM / ML
-> WEB DASHBOARD
-> ASSISTANT IA
-> PDF / informes
```

El dashboard es el producto principal. PDF/PPT son salidas estáticas complementarias.

## Performance Score congelado

Versión:

```text
performance_score_v0.1-experimental
```

Arquitectura:

```text
raw data
-> FEATURE-01
-> semántica NULL/0 validada PERF-11
-> percentiles dentro del grupo posicional
-> dimensiones PERF
-> AVAILABLE_3PLUS
-> pesos posicionales experimentales
-> performance_score 0-100
-> score_evidence_confidence
```

Grupos posicionales:

```text
CB
FB_WB
DM_CM
AM_W
ST
```

Porteros mantienen un camino separado.

## PERF-11 — NULL vs zero

Validado:

```text
shots_total NULL -> 0 cuando el evento observado no ocurrió
goals NULL       -> 0 cuando el evento observado no ocurrió
red_cards NULL   -> 0 cuando el evento observado no ocurrió
yellow_cards     -> NO reinterpretar como 0
```

## PERF-13 — política seleccionada

Candidato aprobado para continuar:

```text
AVAILABLE_3PLUS + ROLE_AWARE
```

Resultados principales:

```text
5D      100/552 = 18.12%
4PLUS   286/552 = 51.81%
3PLUS   485/552 = 87.86%
2PLUS   552/552 = 100.00%
```

GLOBAL vs ROLE_AWARE 3PLUS:

```text
Spearman = 0.9419
mean absolute delta = 2.29
```

La media igual de dimensiones no se congeló porque `creation_progression` dominaba demasiado la sensibilidad agregada.

## PERF-14 — cerrado

Issue #87 cerrado tras validación local.

Resultado final v2:

```text
outfield_rows                  = 552
observable_mapped_role_rows    = 380
eligible_rows_observable_roles = 304
coverage_rate_observable_roles = 0.8000
source_role_unavailable_rows   = 172
total_outfield_coverage_rate   = 0.5507
spearman_vs_unweighted_3plus   = 0.8964
```

Cobertura por grupo:

```text
CB      53/86 = 61.63%
FB_WB   42/68 = 61.76%
DM_CM   89/95 = 93.68%
AM_W    58/65 = 89.23%
ST      62/66 = 93.94%
```

Los 172 `Substitute` no son un fallo del score. DATA-02/DSAI-05 establece que la fuente no ofrece rol táctico fiable para esas apariciones. No se imputa desde historia, rol modal ni otro partido.

Mapping aprobado:

```text
Defender | Left/Centre              -> CB
Defender | Centre/Right             -> CB
Midfielder | Left/Centre            -> DM_CM
Midfielder | Centre/Right           -> DM_CM
Defensive Midfielder | Left/Centre  -> DM_CM
Midfielder | Left/Right             -> AM_W
Wing Back | Left/Right              -> FB_WB
Striker                              -> ST
```

Sensibilidad de priors: peor Spearman ante perturbaciones +/-1 aproximadamente 0.986–0.989 en los cinco grupos candidatos.

Decisión: `performance_score_v0.1-experimental` queda congelado como baseline experimental de producto. Los priors siguen siendo revisables con más datos o validación externa.

## SCORE-INTEGRATION-01 — cerrado

Archivos:

```text
analytics/build_performance_score.py
app/performance_score_access.py
app/pages/1_Performance_Score.py
app/validate_performance_score.py
```

Tabla materializada:

```text
player_match_performance_score
```

Validación local confirmada:

```text
PERFORMANCE SCORE MATERIALIZATION: COMPLETE
rows_written=552
observable_role_rows=380
eligible_observable_scores=304
coverage_observable_roles=0.8000

PERFORMANCE SCORE DASHBOARD CONTRACT: PASS
rows=552
observable_role_rows=380
eligible_scores=304
coverage_observable_roles=0.8000
source_role_unavailable_rows=172
```

La página Streamlit `Performance Score` fue verificada visualmente con score, confidence, grupo posicional, 5 dimensiones e historial.

Nota operativa local: Streamlit debe leer la misma DuckDB materializada. En el entorno de Sergi:

```powershell
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
```

## DASHBOARD-02 — activo

Issue #88.

Objetivo: convertir el MVP en una herramienta de cuerpo técnico, priorizando la ficha de jugador.

Implementado:

```text
app/pages/2_Jugador.py
```

La vista integrada contiene:

- selector de equipo y jugador;
- apariciones, titularidades, minutos, goles y asistencias;
- descarga de PDF;
- Performance Score;
- confidence de evidencia;
- etiqueta humana del grupo posicional;
- cinco dimensiones;
- evolución temporal del score;
- estado del motor experto N12000/N13000;
- evolución de features;
- historial de partidos.

Etiquetas humanas:

```text
CB      -> Central
FB_WB   -> Lateral / Carriler
DM_CM   -> Migcentre / Interior
AM_W    -> Mitjapunta / Extrem
ST      -> Davanter
GK      -> Porter
```

La página `Performance Score` se mantiene como vista analítica detallada; `Jugador` debe convertirse en la ficha operativa principal.

## Guardrails vigentes

- no copiar fórmulas propietarias Sofascore/FotMob;
- no convertir missing en 0 fuera de PERF-11;
- no threshold bueno/malo sin validación;
- no etiqueta automática de calidad;
- no recomendación táctica derivada directamente del score;
- suplentes sin rol táctico observable no se imputan;
- porteros mantienen camino separado;
- el LLM no calcula ni altera el score;
- el dashboard consume resultados materializados, no recalcula lógica crítica;
- score y expert system se mantienen como capas diferenciadas.

## Siguiente paso exacto

Validar visualmente DASHBOARD-02:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

En el navegador abrir `Jugador` y comprobar:

1. carga de equipo/jugador;
2. score + confidence + posición humana;
3. tabla de dimensiones;
4. evolución del score;
5. motor experto;
6. evolución de métricas;
7. historial;
8. descarga PDF.

Después del check visual:

1. cerrar DASHBOARD-02 fase jugador;
2. integrar score en contexto LLM;
3. integrar score en PDF de jugador;
4. construir Team Mode con tendencias/alertas y vistas de plantilla;
5. pulir navegación/estética para publicación final.