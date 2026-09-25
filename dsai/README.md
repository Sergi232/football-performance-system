# DSAI — Data Science / AI experimental core

Esta carpeta contiene la fase experimental de Data Science / IA del TFM.

## DSAI-01A — feasibility audit

Antes de entrenar modelos se auditan:

- tamaño de muestra;
- cobertura y missingness;
- distribución de roles;
- longitud de secuencias temporales;
- disponibilidad de targets independientes;
- riesgo de leakage;
- baselines posibles;
- viabilidad metodológica de cada caso de uso.

Ejecutar:

```powershell
python dsai\feasibility_audit.py
```

No requiere dependencias nuevas.

Genera localmente:

```text
dsai/output/feasibility_audit.json
dsai/output/feasibility_audit.md
```

Estos outputs son diagnósticos locales y no se deben versionar.

## Estados de viabilidad

- `GO_EXPLORATORY`: se puede estudiar sin target supervisado, pero requiere validación de estabilidad/utilidad.
- `GO_EXPERIMENT`: existe estructura suficiente para diseñar un experimento controlado.
- `CANDIDATE_SUPERVISED`: existe un target observado independiente, pero hay que validar clases, split y baseline antes de entrenar.
- `REFORMULATE_TARGET`: la pregunta es relevante pero el target actual no es defendible.
- `BLOCKED_SHARED_TARGET`: no puede compararse Expert vs ML sin una verdad externa común.
- `BLOCKED_GROUND_TRUTH`: no existe todavía ground truth válido para calibrar una recomendación.

## Regla metodológica

El feasibility audit no crea scores, umbrales, rankings ni recomendaciones. Tampoco usa N12000/N13000 como ground truth para entrenar ML, porque eso produciría una evaluación circular.

La salida del audit decide qué experimentos se implementan después y cuáles se descartan o reformulan.
