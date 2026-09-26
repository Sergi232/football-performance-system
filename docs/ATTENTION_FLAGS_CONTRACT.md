# Attention Flags Contract

Versió: `attention_flags_v0.1-auditable`

## Objectiu

Exposar limitacions explícites de dades, context o evidència sense convertir-les en judicis de rendiment.

## Codis aprovats

- `ROLE_CONTEXT_UNAVAILABLE`: la font no informa d’un rol tàctic fiable i no s’imputa cap posició.
- `INSUFFICIENT_RATING_EVIDENCE`: el motor de Match Rating ha marcat explícitament evidència insuficient i manté un midpoint neutral.
- `GPS_QUALITY_FLAGS_PRESENT`: existeixen mostres GPS amb `quality_flags` i cal revisar la qualitat de l’import.

## No forma part d’aquesta versió

- alerta de baix rendiment;
- fatiga;
- readiness;
- risc de lesió;
- llindars de HSR/sprint;
- recomanacions tàctiques;
- etiquetes bo/dolent.

Aquestes conclusions requeririen regles o models validats específicament.
