# TFM — Checklist de capturas reales del producto

Fecha: 04/10/2026
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

Usar **modo `Local · Qwen`** para la captura canónica, porque es el runtime validado localmente y no depende de una API externa.

Pregunta recomendada:

```text
¿Quién corre más distancia por partido?
```

Alternativas válidas:

```text
¿Cómo ha evolucionado Jugador 01?

Compárame las principales estadísticas de los delanteros

¿Quién ha rendido mejor en la posición de central? Muéstrame las métricas
```

Mostrar:
- selector `Fallback semántico`;
- modo `Local · Qwen`;
- pregunta;
- respuesta en castellano;
- identidades demo (`Equipo Demo`, `Jugador XX`, `Rival XX`) cuando corresponda;
- expander `Evidencia consultada` abierto;
- `Ruta: determinista + herramientas FPS` cuando la consulta sea clara;
- `LLM utilizado: no` en la captura determinista;
- tool/consulta estructurada legible;
- referencia a Python / DuckDB / analytics materializados.

La captura canónica debe mostrar una consulta con `rounds=0` internamente, presentada al usuario como **ruta determinista sin uso de LLM**. Esto evidencia que el modelo de lenguaje es un fallback de interpretación y no el motor que calcula la respuesta.

Uso:
- demostrar la capa conversacional downstream de analytics y la arquitectura deterministic-first.

No usar como captura canónica:
- una API key real visible;
- XI ideal;
- riesgo de lesión;
- recomendación táctica automática;
- `mejor jugador`, `más completo` o `más determinante` sin métrica/criterio explícito.

Las comparaciones por posición **sí están validadas** cuando el criterio se declara de forma explícita. Si se pregunta quién ha rendido mejor dentro de una posición, el sistema ordena por Match Rating medio de esa muestra y enseña métricas descriptivas adicionales; no crea un score nuevo.

El selector `OpenAI API · clave propia` puede aparecer como opción disponible, pero no es necesario activarlo ni mostrar una key para cerrar el MVP.

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

Mostrar una página representativa del informe de jugador con identidad demo/anónima.

---

## Captura 10 — PDF Match

Mostrar una página representativa del informe de partido con rival demo/anónimo.

---

# Capturas opcionales para anexos/defensa

- pantalla de selección de modos;
- detalle de un nodo del sistema experto;
- historial temporal de un jugador;
- ejemplo de máscara `Equipo Demo / Jugador XX / Rival XX`;
- comparación por posición con criterio explícito;
- selector Local/OpenAI del Coach Copilot sin mostrar claves;
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
5. tiene una función argumental clara dentro de la memoria;
6. no expone API keys, rutas privadas o identidades profesionales reales.
