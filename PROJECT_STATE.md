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
DASHBOARD-02                        ACTIVO — ISSUE #88 / REDISEÑO PROFESIONAL PLAYER VIEW
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

El dashboard web es el producto principal. PDF/PPT son salidas estáticas complementarias.

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

Porteros mantienen camino separado.

## Validaciones del score

PERF-13 seleccionó:

```text
AVAILABLE_3PLUS + ROLE_AWARE
```

Cobertura:

```text
5D      100/552 = 18.12%
4PLUS   286/552 = 51.81%
3PLUS   485/552 = 87.86%
2PLUS   552/552 = 100.00%
```

PERF-14 final:

```text
outfield_rows                  = 552
observable_mapped_role_rows    = 380
eligible_rows_observable_roles = 304
coverage_rate_observable_roles = 0.8000
source_role_unavailable_rows   = 172
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

Los 172 `Substitute` no se imputan: DATA-02/DSAI-05 establece que la fuente no ofrece rol táctico fiable para esas apariciones.

Sensibilidad de priors: peor Spearman ante perturbaciones +/-1 aproximadamente 0.986–0.989 en los cinco grupos candidatos.

Decisión: `performance_score_v0.1-experimental` queda congelado como baseline experimental de producto. Los priors son revisables con más datos o validación externa.

## SCORE-INTEGRATION-01 — cerrado

Tabla materializada:

```text
player_match_performance_score
```

Archivos:

```text
analytics/build_performance_score.py
app/performance_score_access.py
app/pages/1_Performance_Score.py
app/validate_performance_score.py
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

Nota operativa local:

```powershell
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
```

## DASHBOARD-02 — activo

Issue #88.

Objetivo: que el producto parezca una plataforma profesional de sports performance y no un prototipo Python/Streamlit.

### Criterio UX aprobado

La interfaz para entrenador debe priorizar:

- lectura rápida;
- jerarquía visual;
- KPIs de staff;
- etiquetas humanas;
- tendencias y alertas;
- acceso progresivo al detalle;
- metodología/IDs técnicos ocultos en expanders o vistas de auditoría.

No mostrar en primer plano nombres internos como `AM_W`, `N12000.170`, `score_version` o nombres de columnas.

### Rediseño profesional implementado

Archivos:

```text
.streamlit/config.toml
app/ui_theme.py
app/pages/1_Performance_Score.py
app/pages/2_Jugador.py
```

`app/ui_theme.py` añade:

- identidad visual común;
- sidebar oscura;
- fondo y tarjetas profesionales;
- cabecera de jugador;
- score cards;
- barras de dimensiones;
- etiquetas posicionales humanas.

`Jugador` se organiza ahora en:

```text
Resum
Evolució
Tècnic
Motor expert
Partits
```

Incluye:

- cabecera de jugador/equipo/rol;
- apariciones, titularidades, minutos, goles y asistencias;
- Performance Score + confidence + posición humana;
- dimensiones 0–100 como barras;
- evolución del score;
- últimas observaciones;
- evolución de features;
- tabla técnica player-match;
- motor experto con detalle técnico oculto;
- historial con score/confidence;
- exportación PDF.

La página `Performance Score` detallada utiliza el mismo lenguaje visual.

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
- score y expert system son capas diferentes.

## Siguiente paso exacto

Validar visualmente el rediseño profesional:

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
$env:FPS_DB_PATH = "D:\Data\Sergi\Desktop\football-performance-system\data\football_performance.duckdb"
streamlit run app\streamlit_app.py
```

Abrir `Jugador` y revisar especialmente `Resum`.

Después del check visual, sin reabrir metodología del score:

1. construir Team Mode profesional: plantilla + forma + tendencias + alertas;
2. integrar Performance Score en contexto LLM;
3. integrar score/evolución en PDF de jugador;
4. construir vistas físicas/GPS;
5. pulir navegación global para publicación final.
