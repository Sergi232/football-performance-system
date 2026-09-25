# Analytics Engine

ANALYTICS-01 ocupa la capa entre Feature Engine y Decision Engine.

Su función es convertir features ya validadas en **evidencia estructurada y auditable**, sin emitir todavía recomendaciones tácticas.

## Decisión DG-AN-01

Aprobada opción C: se mantienen dos comparaciones separadas.

### SELF_ROLE_PRIOR

Compara el valor actual del jugador con su propio historial estrictamente anterior en el mismo `primary_role` observado.

La referencia reutiliza FEATURE-03; Analytics no recalcula una segunda historia temporal independiente.

### PEER_ROLE_PRIOR

Compara el valor actual con otros jugadores del mismo equipo y mismo rol observado usando solo datos anteriores a la fecha actual.

Reglas:
- el jugador actual queda excluido del peer pool;
- la misma fecha no entra en la referencia;
- cada peer aporta primero su media strict-past en ese rol;
- después se calcula la distribución entre peers;
- así un jugador con más partidos no pesa más que otro por tener más observaciones.

## Salida

Tabla `analytics_evidence`.

Campos principales:
- jugador / partido / rol / feature;
- `comparison_scope`;
- valor actual;
- número de observaciones de referencia;
- número de jugadores de referencia;
- media / mediana / desviación de referencia;
- pendiente previa cuando existe en self-history;
- delta respecto a la media;
- dirección matemática `ABOVE_MEAN / BELOW_MEAN / EQUAL_MEAN`;
- estado de evidencia.

## Lo que ANALYTICS-01 no hace

No crea:
- score global;
- ranking;
- percentil;
- etiqueta bueno/malo;
- mínimo de muestra arbitrario;
- confianza de recomendación;
- recomendación táctica.

Los conteos de muestra quedan expuestos para que una policy posterior pueda validarlos con datos/literatura/experimentos.

## Validación local

No requiere dependencias nuevas.

```powershell
python analytics\validate_stage1.py
```

El validador reconstruye la capa y comprueba:
- dos scopes por cada FEATURE-01;
- identidad de SELF_ROLE_PRIOR con FEATURE-03;
- strict-past peer comparison;
- exclusión del jugador actual;
- ponderación igual por peer;
- ausencia de campos evaluativos no aprobados.
