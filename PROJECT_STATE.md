# PROJECT_STATE

Última actualización: 26/09/2026

Memoria técnica operativa del proyecto. Si contradice un chat antiguo, prevalece este archivo.

## Estado actual

```text
PERF-11 NULL VS ZERO SEMANTICS      CERRADO / 3 VALIDATED CANDIDATES — ISSUE #77
PERF-12 VALIDATED ZERO IMPACT       ACTIVO — ISSUE #78 / SCRIPT IMPLEMENTADO
```

## PERF-11 — resultado

`shots_total`, `goals` y `red_cards`: `EVENT_VALIDATED_NULL_AS_ZERO_CANDIDATE`.
`yellow_cards`: `NULL_AS_ZERO_NOT_VALIDATED` por 5 contradicciones.

## PERF-12 — objetivo

Aplicar solo en memoria la semántica validada para medir impacto de cobertura antes de cambiar FEATURE-01 o la política del score.

## Siguiente paso exacto

```powershell
cd C:\Users\sergi\Desktop\football-performance-system
git pull
python dsai\performance_validated_zero_impact.py
```

No instalar nada.
