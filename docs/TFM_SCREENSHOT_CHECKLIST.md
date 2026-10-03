# TFM — Checklist de capturas reales del producto

Fecha: 03/10/2026
Estado: pendiente de ejecución visual sobre el producto real.

Objetivo: definir exactamente qué capturas deben producirse para la memoria y la defensa. Estas capturas deben salir de la aplicación real ejecutada; no deben sustituirse por mockups.

---

## Captura 1 — Data Collector V1.1

Mostrar:
- cabecera de partido;
- jugador seleccionado;
- botones de acciones principales;
- contexto de rol/minutos;
- interfaz en castellano.

Evitar:
- datos personales/reales identificables si el modo demo no está activo;
- afirmar revisión visual móvil si la captura es desktop.

Uso:
- metodología / implementación del Collector.

Pie sugerido:

> Interfaz del Data Collector V1.1 utilizada para registrar eventos observables y contexto de jugador-partido.

---

## Captura 2 — Team Mode

Mostrar:
- `Equipo Demo`;
- resumen de forma/rendimiento;
- plantilla;
- Match Rating o evolución;
- navegación visible.

Uso:
- sección de producto.

Pie sugerido:

> Team Mode de la aplicación, con indicadores agregados, evolución y acceso a la plantilla del equipo.

---

## Captura 3 — Player Mode

Mostrar:
- `Jugador XX`;
- Match Rating;
- evolución temporal;
- rol/contexto;
- evidencia experta o Performance Index si aparece en la misma vista.

Uso:
- demostrar análisis longitudinal de jugador.

---

## Captura 4 — Match Mode

Mostrar:
- `Rival XX`;
- jugadores del partido;
- ratings;
- minutos/rol/confianza;
- observaciones deterministas si son visibles.

Uso:
- demostrar funcionamiento desde un partido concreto.

---

## Captura 5 — Físico / GPS

Mostrar:
- etiqueta explícita de GPS sintético/demo;
- distancia/velocidad u otros resúmenes descriptivos disponibles;
- contexto de partido/jugador.

No mostrar como claim:
- fatiga;
- readiness;
- riesgo de lesión;
- zonas HSR/sprint no validadas.

Pie sugerido:

> Vista física descriptiva basada en la capa GPS normalizada; la demo sintética se etiqueta explícitamente y no se utiliza como evidencia fisiológica real.

---

## Captura 6 — Attention Centre

Mostrar:
- flags auditables de contexto/calidad;
- ausencia de claims médicos o de fatiga.

Uso:
- explicar que las alertas son de calidad/evidencia y no diagnósticas.

---

## Captura 7 — Coach Copilot

Pregunta recomendada:

```text
¿Cómo ha evolucionado este jugador?
```

o una pregunta equivalente que esté dentro del contrato validado.

Mostrar:
- pregunta;
- respuesta en castellano;
- contexto de jugador/equipo;
- sin recomendaciones no validadas.

Uso:
- demostrar la capa conversacional downstream de analytics.

Evitar preguntas de:
- XI ideal;
- riesgo de lesión;
- ranking de rol no validado;
- recomendación táctica automática.

---

## Captura 8 — PDF Team

Mostrar:
- portada o página principal;
- visual limpio;
- `Equipo Demo`;
- gráficos/resultados materializados.

Uso:
- demostrar salida estática complementaria.

---

## Captura 9 — PDF Player

Mostrar una página representativa del informe de jugador.

---

## Captura 10 — PDF Match

Mostrar una página representativa del informe de partido.

---

# Capturas opcionales para anexos/defensa

- pantalla de selección de modos;
- detalle de un nodo del sistema experto;
- historial temporal de un jugador;
- ejemplo de máscara `Equipo Demo / Jugador XX / Rival XX`;
- GitHub Actions con CI en verde;
- árbol del repositorio.

---

# Convención de archivos

Guardar las capturas finales con nombres estables:

```text
docs/screenshots/01_collector.png
docs/screenshots/02_team_mode.png
docs/screenshots/03_player_mode.png
docs/screenshots/04_match_mode.png
docs/screenshots/05_gps.png
docs/screenshots/06_attention.png
docs/screenshots/07_coach_copilot.png
docs/screenshots/08_pdf_team.png
docs/screenshots/09_pdf_player.png
docs/screenshots/10_pdf_match.png
```

# Criterio de aceptación

Una captura entra en la memoria solo si:

1. procede del producto real;
2. usa modo demo/anónimo cuando corresponda;
3. no muestra claims fuera del alcance validado;
4. es legible a tamaño de página;
5. tiene una función argumental clara dentro de la memoria.