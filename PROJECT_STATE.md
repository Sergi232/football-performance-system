# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## Estado actual

```text
PERF-10 COVERAGE / OBSERVABILITY    CERRADO / POLICY REDESIGN REQUIRED — ISSUE #70
PERF-11 NULL VS ZERO SEMANTICS      CERRADO / 3 VALIDATED CANDIDATES — ISSUE #77
PERF-12 VALIDATED ZERO IMPACT       ACTIVO — ISSUE #78 / SCRIPT IMPLEMENTADO
```

## Objetivo principal confirmado

El objetivo analítico central es adjudicar un score de rendimiento jugador-partido.

## PERF-11 — resultado

```text
shots_total -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
goals -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
yellow_cards -> NULL_AS_ZERO_NOT_VALIDATED (5 contradicciones)
red_cards -> EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE
```

## PERF-12 — activo

`dsai/performance_validated_zero_impact.py` aplica solo en memoria la semántica validada y compara cobertura antes/después. No modifica DB, FEATURE-01, pesos, thresholds, rankings ni recomendaciones.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_validated_zero_impact.py
```
