# TFM — Checklist final de entrega

Fecha: 04/10/2026

Objetivo: controlar el cierre del TFM sin reabrir funcionalidad ya validada.

---

# A. Producto técnico

- [x] Data Collector V1.1 cerrado.
- [x] Esquema DuckDB cerrado.
- [x] FEATURE-01/02/03 validados.
- [x] Analytics validado.
- [x] Expert N1000-N13000 validado.
- [x] Match Rating V5 validado y congelado.
- [x] Performance Index separado como experimental.
- [x] GPS normalization validada.
- [x] GPS physical summary validado.
- [x] Team Mode operativo.
- [x] Player Mode operativo.
- [x] Match Mode operativo.
- [x] Attention Centre operativo.
- [x] Coach Copilot local cerrado con smoke real **28/28 PASS · avg 0.4s**.
- [x] Query-space contract del Coach Copilot validado en CI.
- [x] Comparaciones por posición validadas con criterio explícito.
- [x] Preflight/guardrails evitan LLM para ruido, meta-consultas y fuera de dominio obvio.
- [x] Anonimización del Assistant validada contractualmente para demo.
- [x] OpenAI BYOK opcional implementado con contract tests + CI PASS.
- [x] Reports V6 cerrados.
- [x] Access control contractual validado.
- [x] QA global end-to-end PASS.

---

# B. Reproducibilidad / GitHub

- [x] README actualizado a arquitectura final.
- [x] PROJECT_STATE actualizado a arquitectura final.
- [x] Contrato canónico `llm/COACH_COPILOT_CONTRACT.md` creado.
- [x] Validador automático `llm/validate_coach_contract.py` integrado en CI.
- [x] Smoke real reproducible `llm/smoke_test_coach_agent.py` validado 28/28.
- [x] Demo sintética pública desde cero.
- [x] `professional_source_rows=0`.
- [x] App read layer sobre demo sintética PASS.
- [x] Report payloads sobre demo sintética PASS.
- [x] CI activo en push.
- [x] CI activo en pull_request.
- [x] Pytest en CI.
- [x] Build/validator sintético en CI.
- [x] Query-space contract en CI.
- [x] Ejecución limpia de referencia SUCCESS.

---

# C. Memoria académica

- [x] Hipótesis definida.
- [x] Objetivo general definido.
- [x] Objetivos específicos definidos.
- [x] Marco teórico redactado.
- [x] Bibliografía base curada.
- [x] Metodología redactada.
- [x] Resultados redactados con gates reales.
- [x] Discusión redactada.
- [x] Limitaciones redactadas.
- [x] Conclusiones redactadas.
- [x] Trabajo futuro redactado.
- [x] Manuscrito integrado creado.
- [x] Matriz de evidencias creada.
- [x] Tablas canónicas creadas.
- [x] Anexos base redactados.
- [ ] Adaptar a plantilla oficial universidad.
- [ ] Ajustar extensión oficial.
- [ ] Revisar norma bibliográfica oficial.
- [ ] Numerar automáticamente capítulos/figuras/tablas según plantilla.
- [ ] Revisión lingüística final.

---

# D. Figuras y capturas

Figuras técnicas:

- [x] Arquitectura general.
- [x] Coach Copilot / grounding.
- [x] Strict-past.
- [x] Sistema experto.
- [x] Modelo de datos.

Capturas reales:

- [ ] Collector.
- [ ] Team Mode.
- [ ] Player Mode.
- [ ] Match Mode.
- [ ] GPS.
- [ ] Attention Centre.
- [ ] Coach Copilot final con `Local · Qwen`, identidad demo y evidencia visible.
- [ ] PDF Team.
- [ ] PDF Player.
- [ ] PDF Match.

Checklist detallada:
- `docs/TFM_SCREENSHOT_CHECKLIST.md`.

---

# E. Defensa

- [x] Guion base creado.
- [x] Preguntas previsibles preparadas.
- [x] Secuencia de demo propuesta.
- [x] Mensaje central definido.
- [ ] Adaptar a duración oficial.
- [ ] Crear presentación final.
- [ ] Insertar capturas reales.
- [ ] Preparar backup PDF/capturas por si falla la demo.
- [ ] Ensayar defensa.

---

# F. Validaciones opcionales que mejorarían el TFM pero no deben inventarse

- [ ] Estudio interobservador del Collector.
- [ ] Validación con entrenadores/analistas reales.
- [ ] GPS real de proveedor.
- [ ] Validación externa del Match Rating.
- [ ] Ground truth para policy N13000.
- [ ] Comparación Expert vs ML con target independiente.
- [ ] Benchmark live del modo OpenAI BYOK con API key real.

Estas tareas son mejoras reales, no requisitos para considerar funcional el prototipo actual.

---

# G. Bloqueos externos actuales

## Plantilla/rúbrica universitaria

Pendiente si no se ha recibido todavía. Sin ella no puede cerrarse la maquetación definitiva conforme a requisitos oficiales.

## Capturas del producto local

Requieren ejecutar el producto en el PC y capturar pantallas reales. Son el principal bloque pendiente controlable antes de la entrega.

## Derechos del dataset profesional

No publicar ni redistribuir mientras no exista autorización/licencia explícita. La demo sintética separada sí tiene contrato redistribuible.

---

# H. Orden operativo de cierre hoy

```text
1  git pull --ff-only
2  reconstruir / abrir demo sintética con FPS_DEMO_MODE=1
3  comprobar visualmente identidades Equipo Demo / Jugador XX / Rival XX
4  producir las 10 capturas canónicas
5  adaptar memoria a plantilla disponible
6  revisión final de bibliografía / idioma / numeración
7  preparar presentación y backup estático
8  guardar copia final del repo + memoria + capturas
9  entregar
```

No volver a hacer testing manual aleatorio del Coach Copilot. El gate funcional está cerrado con `28/28 PASS`; solo reabrirlo ante un defecto reproducible que invalide el contrato.

---

# Criterio de cierre final

El TFM estará listo para entrega cuando se cumpla:

```text
producto validado              ✅
Coach Copilot real 28/28       ✅
GitHub reproducible            ✅
memoria académica              ✅ contenido base
figuras técnicas               ✅
capturas reales                pendiente
plantilla/maquetación oficial  pendiente si aplica
defensa final                  pendiente
```

No añadir nueva funcionalidad deportiva salvo que aparezca un defecto real que invalide un contrato ya cerrado.
