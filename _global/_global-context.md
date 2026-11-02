---
date: 2026-11-01T17:30:00+01:00
project: _global
type: context
status: active
tags:
  - proyecto/contexto
evidence:
  - "PROTOCOL.md"
needs_review: false
answers_questions:
  - "¿Cuáles son las preferencias globales de trabajo y estándares del usuario?"
---

# Contexto Global y Preferencias de Trabajo

> Este documento define las pautas de interacción, estándares de codificación y preferencias de entorno transversales a todos los proyectos.

## Preferencias de Interacción con Asistentes IA
- Tono: Conciso, directo a la solución técnica.
- Código: Producción directa, modular y tipado; sin código especulativo ni omisión de gestión de errores.
- Autonomía: Ejecutar tareas verificando con pruebas y comprobaciones reales antes de dar por terminado.

## Entorno Local de Desarrollo
- Sistema Operativo: Windows 11
- Shells habituales: PowerShell / Bash
- Control de versiones: Git local
- Gestión de paquetes: Estándar por lenguaje

## Principios de Ingeniería Transversales
- Simplicidad y robustez: Evitar sobreingeniería y dependencias innecesarias.
- Seguridad estricta: Jamás registrar credenciales, API keys ni secretos.
- Observabilidad y reproducibilidad: Todo cambio debe dejar rastro claro de cómo se ejecutó y verificó.
