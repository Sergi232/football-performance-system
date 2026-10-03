# TFM — Guion base de defensa

Fecha: 03/10/2026
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
- captura real de una pregunta validada.

Mensaje clave:

```text
El LLM explica resultados.
No calcula la verdad del sistema.
```

Datos de validación útiles:
- router 17/17;
- agregado 66/68 = 97,1%;
- runtime errors 0;
- safety failures 0;
- smoke local 4/4 PASS.

---

## 10. Validación y reproducibilidad

Mostrar una tabla breve:

```text
QA global              PASS
Demo sintética         PASS
CI entorno limpio      PASS
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

Priorizar solo 3–4:

1. validación con entrenadores;
2. fiabilidad interobservador del Collector;
3. GPS real;
4. policy N13000 / validación externa Match Rating.

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

Pregunta del Copilot recomendada:

```text
¿Cómo ha evolucionado este jugador?
```

Tener preparado un plan B con capturas/PDF si Ollama o Streamlit falla durante la defensa.

---

# Preguntas previsibles del tribunal

## ¿Por qué no usar directamente un LLM para analizar los datos?

Respuesta:
- porque un LLM no debe ser la fuente de cálculo crítico;
- las métricas y decisiones se calculan antes;
- el LLM se limita a consultar y explicar.

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