# memory-scaffold

Plantilla opinionada de memoria para agentes. Un solo comando instala en un
proyecto destino los 13 archivos que le dan a un agente (GLM, Claude, etc.)
contexto de memoria persistente: 9 de memoria de estado, 3 protocolos de
comportamiento y 1 protocolo de auditoría.

## Filosofía

- **Python 3 stdlib pura.** Cero dependencias. Corre en cualquier máquina con Python.
- **Opinionada a propósito.** Instala todo o nada: 13 archivos, sin flags de selección
  ni de idioma. La configurabilidad es deuda, el usuario es uno.
- **El script es estructural, el agente es semántico.** El script crea la estructura,
  renderiza placeholders y valida. No lee `docs/`, no puebla contenido, no inicializa
  git. Poblar (leer specs y volcar a la memoria) es trabajo del agente, guiado por
  `BOOTSTRAP.md`.
- **Frontera de posesión clara.** Los 4 archivos "de sistema" (BOOTSTRAP, INICIO,
  SALIDA, AUDIT) llevan marcadores `scaffold:system` que habilitan un `--upgrade`
  futuro sin tocar el contenido. Los 9 archivos de memoria son del proyecto y se
  protegen siempre: ninguna bandera los pisa.
- **Determinista donde se puede, narrativo donde se debe.** El script garantiza
  estructura, encoding UTF-8 y line endings LF. El agente garantiza que la memoria
  se mantenga verdadera.

## Flujo de uso (5 pasos)

1. **Cloná la plantilla** una vez en una ubicación fija: `git clone ... ~/tools/memory-scaffold`.
2. **Bootstrapeá un proyecto destino**:
   `python3 bootstrap.py --project /ruta/al/proyecto` (default: directorio actual).
   Crea `.agent/memory/` con los 13 archivos, sustituye placeholders y reporta warnings.
3. **Poblar (una sola vez, al arrancar el proyecto)**: pedile al agente que ejecute
   `.agent/memory/BOOTSTRAP.md`. El agente lee `docs/` y completa `tech_stack.md`,
   `roadmap.md` e `INDEX.md`. No crea archivos: la estructura ya existe.
4. **Trabajo diario**: el agente arranca leyendo `.agent/memory/INDEX.md` y sigue
   `PROTOCOLO_INICIO.md`; al cerrar, sigue `PROTOCOLO_SALIDA.md` para mantener la
   memoria al día (rotación de sesiones, reglas de oro, observaciones).
5. **Auditar de vez en cuando** (cierre de fase o ~mensual): ejecutar
   `.agent/memory/AUDIT_DRIFT.md` para detectar desajustes entre la memoria y el código real.

## Uso del script

```
python3 bootstrap.py [--project PATH] [--force] [--dry-run] [--verbose]
```

- `--project PATH` — directorio destino (default: actual).
- `--force` — completa instalaciones parciales; jamás pisa memoria con contenido.
- `--dry-run` — muestra el plan sin escribir nada.
- `--verbose` — log detallado por archivo.

Ver `docs/IMPLEMENTATION_PLAN.md` para la especificación completa.
