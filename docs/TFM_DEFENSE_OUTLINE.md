# TFM — Guion base de defensa

Fecha: 04/10/2026
Estado: guion preliminar; adaptar a la duración oficial cuando se conozca.

Objetivo: explicar el proyecto como producto + metodología, no como una lista de scripts.

---

# Mensaje central

> Se ha construido un sistema funcional y auditable que transforma datos simples de vídeo y GPS opcional en información para equipo, jugador y partido, manteniendo separados los cálculos críticos de la capa LLM y evitando inferencias no validadas.

---

# Estructura recomendada

## 1. Problema

Explicar:
- clubes amateur/semiprofesionales pueden tener vídeo y, a veces, GPS;
- normalmente no tienen un departamento de análisis ni proveedores profesionales;
- el problema es transformar datos sencillos en información utilizable.

Mensaje:

```text
No intento construir Opta.
Intento construir un sistema útil con datos que un club pequeño sí puede obtener.
```

---

## 2. Hipótesis y objetivo

Presentar la hipótesis de viabilidad técnica.

Aclarar inmediatamente:
- no se pretende demostrar que el sistema aumente victorias;
- se pretende demostrar que la arquitectura integral es viable, auditable y reproducible.

---

## 3. Arquitectura

Usar:
- `docs/figures/tfm_architecture_overview.svg`.

Explicar el flujo completo en una sola diapositiva.

Idea clave:

```text
dato observado
→ transformación
→ evidencia
→ decisión
→ explicación
```

---

## 4. Data Collector

Mostrar captura real.

Explicar por qué se recogen acciones simples y no métricas avanzadas manuales.

Ejemplo:
- pase completado/fallado sí;
- xG manual no.

---

## 5. Feature Engine y leakage

Usar:
- `docs/figures/tfm_strict_past.svg`.

Explicar que una tendencia histórica solo puede utilizar información disponible antes del partido analizado.

Esta diapositiva demuestra criterio de Data Science, no solo programación.

---

## 6. Sistema experto

Usar:
- `docs/figures/tfm_expert_system.svg`.

Idea clave:
- no es un único `DecisionTreeClassifier`;
- es una jerarquía auditable;
- cada nodo conserva entrada, condición, resultado, confianza y justificación;
- N13000 puede abstenerse.

Mostrar como ejemplo:

```text
POLICY_UNVALIDATED
→ existe evidencia
→ pero no hay recomendación inventada
```

---

## 7. Match Rating + GPS

Explicar dos ideas distintas:

### Match Rating
- valoración inmediata desde partido 1;
- cobertura 590/590 en el caso de desarrollo;
- V5 congelada tras validación técnica.

### GPS
- opcional;
- normalizado a esquema común;
- demo sintética no se interpreta como fisiología real;
- no se infiere fatiga/lesión.

---

## 8. Producto final

Mostrar rápidamente:
- Team Mode;
- Player Mode;
- Match Mode;
- GPS;
- Attention Centre.

No dedicar demasiado tiempo a navegar por todas las pantallas.

La defensa debe explicar qué decisión ayuda a tomar cada vista.

---

## 9. Coach Copilot

Usar:
- `docs/figures/tfm_llm_grounding.svg`;
- captura real del asistente final.

Mensaje clave:

```text
El LLM interpreta lenguaje cuando hace falta.
Python/DuckDB calcula los resultados.
```

Arquitectura a explicar:

```text
pregunta clara
→ router determinista
→ tool read-only
→ DuckDB / analytics
→ respuesta

pregunta ambigua
→ Qwen local o OpenAI BYOK opcional
→ tool validada
→ DuckDB / analytics
→ evidencia
→ respuesta grounded
```

Datos de validación que sí pueden citarse:

```text
SMOKE CONTRACT = PASS (22/22)
average_elapsed = 1.4s
consultas deterministas típicas = 0.1–0.8s
follow-ups = 0.1–0.2s
```

Aclaración importante:
- el fallback Qwen puede tardar decenas de segundos en CPU;
- el modo OpenAI existe como opción BYOK y pasa contratos/CI, pero no se ha benchmarkeado live con una API key real.

Pregunta recomendada en demo:

```text
¿Quién corre más distancia por partido?
```

Abrir `Evidencia consultada` y señalar que las rondas de interpretación semántica son `0` en una pregunta clara.

---

## 10. Validación y reproducibilidad

Mostrar una tabla breve:

```text
QA global              PASS
Demo sintética         PASS
CI entorno limpio      PASS
Coach Copilot 22/22    PASS
```

Explicar la separación:

```text
software reproducible
≠
derecho a redistribuir dataset profesional
```

La demo pública se genera desde cero y contiene 0 filas profesionales.

---

## 11. Resultado / contraste de hipótesis

Conclusión:

> La hipótesis queda contrastada favorablemente como viabilidad técnica y arquitectónica.

No queda demostrado:
- mejora real de decisiones de entrenadores;
- mejora deportiva;
- fatiga/lesión;
- rol táctico óptimo.

---

## 12. Limitaciones y futuro

Priorizar solo 4–5:

1. validación con entrenadores;
2. fiabilidad interobservador del Collector;
3. GPS real;
4. policy N13000 / validación externa Match Rating;
5. validación live de proveedores externos si se quiere comercializar ese modo.

Cerrar mostrando que el proyecto ya es funcional y que el futuro consiste en validar mejor, no en añadir complejidad indiscriminadamente.

---

# Demo en directo recomendada

Orden máximo:

```text
Team Mode
→ Player Mode
→ Coach Copilot
→ export PDF
```

No navegar por toda la aplicación.

Pregunta principal del Copilot:

```text
¿Quién corre más distancia por partido?
```

Follow-up opcional si hay tiempo:

```text
¿Y el segundo?
```

Tener preparado un plan B con capturas/PDF si Ollama o Streamlit falla durante la defensa. Las consultas deterministas principales pueden seguir funcionando aunque Ollama no esté disponible.

---

# Preguntas previsibles del tribunal

## ¿Por qué no usar directamente un LLM para analizar los datos?

Respuesta:
- porque un LLM no debe ser la fuente de cálculo crítico;
- las métricas y decisiones se calculan antes;
- para preguntas claras ni siquiera hace falta activar el LLM;
- el LLM se reserva para interpretar lenguaje ambiguo y explicar evidencia estructurada.

## ¿Entonces dónde está la IA generativa?

Respuesta:
- existe como capa de interacción;
- Qwen local actúa como fallback semántico;
- opcionalmente puede usarse OpenAI con API key del usuario;
- ambas opciones están desacopladas del motor analítico.

## ¿Por qué sistema experto y no ML?

Respuesta:
- el producto necesitaba auditabilidad inmediata;
- no existe ground truth independiente suficiente para todas las recomendaciones;
- ML se probó experimentalmente y solo debe incorporarse cuando supere un baseline simple de forma defendible.

## ¿El Match Rating está científicamente validado?

Respuesta:
- está validado técnicamente dentro del producto;
- no se afirma una validez universal externa;
- una validación con expertos/outcomes independientes es trabajo futuro.

## ¿Por qué GPS sintético?

Respuesta:
- para validar integración y producto sin depender de un proveedor real;
- está explícitamente etiquetado;
- no alimenta evidencia física observada del experto.

## ¿Cómo evitas data leakage?

Respuesta:
- FEATURE-02/03 y Analytics utilizan strict-past;
- solo observaciones con fecha anterior a t;
- existe validación contractual específica.

## ¿Por qué permitir OpenAI si ya existe Qwen?

Respuesta:
- no es una dependencia del producto;
- es una opción para usuarios que prefieran un modelo externo más capaz para lenguaje complejo;
- la misma capa analítica y las mismas tools siguen siendo la fuente de verdad;
- el usuario aporta su propia API key.

## ¿Qué demuestra realmente el TFM?

Respuesta:
- viabilidad técnica, auditabilidad y reproducibilidad de la arquitectura;
- no impacto causal sobre resultados deportivos.

---

# Criterio para la defensa

La presentación debe transmitir tres cosas:

```text
1. existe un producto real
2. existe criterio metodológico detrás
3. conocemos exactamente los límites de lo que podemos afirmar
```

Si estas tres ideas quedan claras, no es necesario enseñar cada función del repositorio.
