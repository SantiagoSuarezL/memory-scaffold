PLAN DE TRABAJO — Plantilla de Memoria para Agentes

1. Decisiones cerradas (no re-discutir en implementación)
| # | Decisión | Justificación breve |
|---|----------|---------------------|
| D1 | Python 3, **stdlib pura** (pathlib, argparse, datetime, shutil) | Cero dependencias, corre en cualquier máquina con Python. El usuario desarrolla en Python y en Windows. |
| D2 | Repo **privado** en GitHub, clonado una vez en ubicación fija (`~/tools/`) | Actualización centralizada; el script se ejecuta *desde* la plantilla *hacia* el proyecto destino. |
| D3 | El script instala **13 archivos**: 9 de memoria + 3 protocolos + 1 audit | Un solo comando deja el proyecto 100% listo. |
| D4 | El script **no lee** `docs/`, **no puebla** contenido, **no inicializa** git | Frontera script/agente: lo determinista vs lo semántico. |
| D5 | BOOTSTRAP.md se **reduce** a solo-poblar (la creación muere) | El script ya creó todo; el agente solo llena desde `docs/`. |
| D6 | Los 3 protocolos + AUDIT llevan **marcadores de bloque** `<!-- scaffold:system:start -->` / `<!-- scaffold:system:end -->` desde el día 1 | Habilita `--upgrade` (implementado en Fase 4) sin tocar contenido de memoria. Los 9 archivos de memoria **no** llevan marcadores (el usuario los posee). |
| D7 | Encoding UTF-8, line endings LF, `.gitattributes` con `* text=auto eol=lf` | Evita el clásico dolor CRLF en Windows/git. |
| D8 | Idioma: español, voseo rioplatense (voz actual del usuario) | Consistencia con los protocolos existentes. |



2. Estructuras

2.1 Repo plantilla (el que clonas en ~/tools/)

memory-scaffold/                    # nombre tentativo — decisión libre del usuario
├── README.md                       # doc humana: qué es, flujo de uso, filosofía
├── .gitattributes
├── bootstrap.py                    # script único, entry point
├── templates/
│   ├── system/                     # archivos "de sistema" (llevan marcadores D6)
│   │   ├── BOOTSTRAP.md
│   │   ├── PROTOCOLO_INICIO.md
│   │   ├── PROTOCOLO_SALIDA.md
│   │   └── AUDIT_DRIFT.md
│   └── memory/                     # archivos "de estado" (sin marcadores)
│       ├── INDEX.md
│       ├── session_log.md
│       ├── session_log_archive.md
│       ├── lessons_learned.md
│       ├── lessons_learned_archive.md
│       ├── tech_stack.md
│       ├── roadmap.md
│       ├── observations.md
│       └── observations_archive.md
├── tests/
│   ├── test_render.py              # placeholders, marcadores
│   ├── test_install.py             # escenarios de instalación
│   ├── test_safety.py              # no-sobrescritura, casos edge
│   └── test_upgrade.py             # semántica de --upgrade (Fase 4)
└── docs/
    └── IMPLEMENTATION_PLAN.md      # este documento (meta: la plantilla nace con su propio método)

2.2 Estructura instalada en el proyecto destino

proyecto-destino/
├── .agent/
│   └── memory/
│       ├── INDEX.md                # el mapa — se lee SIEMPRE primero
│       ├── PROTOCOLO_INICIO.md     # se pega al arrancar sesión
│       ├── PROTOCOLO_SALIDA.md     # se pega al cerrar sesión
│       ├── BOOTSTRAP.md            # se ejecuta UNA sola vez (reducido)
│       ├── AUDIT_DRIFT.md          # bajo demanda explícita, ~mensual
│       ├── session_log.md             # ───┐
│       ├── session_log_archive.md     #    │
│       ├── lessons_learned.md         #    │
│       ├── lessons_learned_archive.md #    │ memoria de estado
│       ├── tech_stack.md              #    │ (rotación gestionada por
│       ├── roadmap.md                 #    │  PROTOCOLO_SALIDA)
│       ├── observations.md            #    │
│       └── observations_archive.md    # ───┘
├── docs/                           # specs del proyecto (PRD, ARCHITECTURE, etc.)
└── graphify-out/                   # asumido presente (D-graphify)

Nota de diseño: INDEX.md debe categorizar los 13 archivos en tres clases de lectura: Siempre (INDEX + los 5 activos), Nunca automático (los 4 archives), Bajo demanda explícita (BOOTSTRAP: solo primera vez; AUDIT_DRIFT: solo cuando el usuario lo invoca). Esta tercera categoría es nueva respecto a tu INDEX actual.

3. Especificación funcional de bootstrap.py

3.1 Interfaz CLI

python3 bootstrap.py [--project PATH] [--force] [--dry-run] [--verbose] [--upgrade]

--project PATH   Directorio destino. Default: directorio actual.
--force          Permite sobrescribir archivos existentes (ver 3.4).
--dry-run        Muestra qué haría sin escribir nada. Imprime árbol resultante.
--verbose        Log detallado de cada archivo procesado.
--upgrade        Reemplaza solo bloques scaffold:system en destinos existentes (no toca memoria).

Sin flags de idioma, sin flags de selección de archivos: la plantilla es opinionada, instala todo o nada. La configurabilidad es deuda; el usuario es uno.

3.2 Pipeline de renderizado
Todos los templates pasan por el mismo pipeline (aunque no tengan placeholders — consistencia):
leer template → sustituir placeholders → envolver en marcadores (solo system/) → escribir destino

Placeholders disponibles:
| Token | Se reemplaza por | Fuente |
|-------|------------------|--------|
| `{{FECHA}}` | Fecha ISO actual (`YYYY-MM-DD`) | `datetime.date.today()` |
| `{{PROYECTO}}` | Nombre del directorio destino | `Path(...).name` |
| `{{AUTOR}}` | `git config user.name` del destino; fallback `"unknown"` | subprocess silencioso |

Si un placeholder queda sin sustituir por error de tipeo en el template, el script debe fallar en tests (no en producción — ver 5.2).

3.3 Comportamiento por defecto (modo install)
Resolver y validar --project: existe, es directorio, tiene permisos de escritura.
Verificar si .agent/memory/ existe:
No existe → crear estructura completa (13 archivos renderizados).
Existe → entrar en modo verify (ver 3.4).
Verificaciones de entorno (warnings, nunca bloquean):
¿docs/ existe en destino? Si no: warning "BOOTSTRAP.md no tendrá specs que leer al poblar".
¿Destino es repo git? Si no: warning "se recomienda git init antes del primer commit de memoria".
Reporte final: árbol de archivos creados + placeholders sustituidos + warnings.

3.4 Modo verify (.agent/memory/ ya existe)
Comportamiento no destructivo por defecto:
Lista qué archivos de los 13 faltan.
Para los existentes: reporta si contienen marcadores scaffold: (protocolos modernos) o no (instalación manual antigua).
No modifica nada. Sugiere: "faltan N archivos; corre con --force para completar, o --dry-run para ver el plan".

3.5 --force: semántica exacta
--force es peligroso por diseño — puede pisar memoria acumulada. Reglas:
Solo aplica a archivos faltantes o idénticos al template renderizado (comparación post-render).
Si un archivo existente difiere del template (tiene contenido del usuario): rechazarlo y listar cuáles fueron protegidos, salvo confirmación interactiva explícita archivo por archivo. En --dry-run + --force, mostrar qué sería protegido vs pisado.
Los archivos de memoria (memory/) con cualquier contenido no-vacío son siempre protegidos — no existe flag que los pise. Esto es un invariante de seguridad, no una preferencia.

3.6 Casos edge a cubrir (GLM: convertir en tests)

| Caso | Comportamiento esperado |
|------|------------------------|
| Destino no existe | Error limpio, exit code 1 |
| `.agent/` existe sin `memory/` | Crear `memory/` dentro, normal |
| Instalación parcial (5 de 13 archivos) | Modo verify completa los 8 faltantes |
| Paths con espacios (Windows) | Funciona (usar `pathlib`, nunca strings concatenados) |
| Correr desde dentro del propio repo plantilla | Warning: "parece que estás bootstrapeando la plantilla en sí misma" |
| Python < 3.8 | Error claro al inicio (version check) |
| Template con placeholder desconocido | El render lanza excepción — test unitario lo garantiza |

3.7 Lo que el script explícitamente NO hace
No lee ni interpreta docs/ del destino.
No ejecuta git init ni ningún comando git mutante.
No instala/configura graphify.
No modifica AGENTS.md/CLAUDE.md del destino. Decisión de Fase 4: el recordatorio automático se
descartó — el contexto se carga manual en cada sesión.

4. Especificación de templates — archivos de sistema
Estos cuatro llevan marcadores <!-- scaffold:system:start --> / <!-- scaffold:system:end --> envolviendo todo su contenido (para --upgrade, Fase 4: reemplazo solo del bloque scaffold, sin tocar el resto).

4.1 BOOTSTRAP.md (rediseño completo — nueva versión)
Fuente: el BOOTSTRAP actual del usuario, con los Pasos 1 y 5 eliminados (los hace el script). Estructura de la nueva versión:

PROTOCOLO DE BOOTSTRAP (correr UNA sola vez, al arrancar el proyecto)
La estructura de .agent/memory/ ya existe (la creó el script de scaffold). Tu trabajo acá es solo POBLAR. No crees archivos.

Paso 1 — Leer los docs UNA vez completos
[idéntico al Paso 2 actual: README + todo docs/, única lectura sin criterio de selección en todo el proyecto]

Paso 2 — Poblar tech_stack.md
[idéntico al Paso 3 actual]

Paso 3 — Poblar roadmap.md
[idéntico al Paso 4 actual: fases desde IMPLEMENTATION_PLAN.md; si no hay fases explícitas, proponer división y esperar confirmación]

Paso 4 — Actualizar INDEX.md
[idéntico al Paso 6 actual: Fase actual 0, próxima fase 1]

Paso 5 — Confirmar
[idéntico al Paso 7 actual: stack detectado, fases, preguntas antes de asumir]

Nota sobre archivos ya existentes
Los 9 archivos de memoria existen con su estructura vacía. Verificá que los headers estén intactos al escribir; no los regeneres.

Cambio clave respecto al original: el paso de verificación (Paso 1 viejo, 11 archivos) desaparece porque es imposible que falten — el script es la fuente de verdad estructural. El agente pierde la responsabilidad (y el gasto de tokens) de crear.

4.2 PROTOCOLO_INICIO.md (casi intacto — 2 cambios)
Fuente: el PROTOCOLO_INICIO actual del usuario. Cambios exactos:
En el punto 3 (lista de archivos "Nunca automático"), agregar: los *_archive.md más BOOTSTRAP.md y AUDIT_DRIFT.md (estos dos últimos solo bajo invocación explícita del usuario).
Sin otros cambios. El punto 3.5 (graphify) queda tal cual — es tu integración y funciona.

4.3 PROTOCOLO_SALIDA.md (casi intacto — 1 cambio)
Fuente: el PROTOCOLO_SALIDA actual del usuario. Cambio exacto:
En la sección 5 (session_log.md, MANDATORIO), agregar a la especificación del formato de entrada de sesión:

Primera línea de la sesión nueva (obligatoria):
Sesión N — {{FECHA}} — [modelo + harness que ejecutó: ej. "GLM 4.6 vía OpenCode"]

Esto es lo único que rescato de agent-work-mem: identidad del agente en el historial. Si mañana cambias de modelo, sabrás qué reglas se aprendieron bajo cuál. Cuesta una línea por sesión.

4.4 AUDIT_DRIFT.md (nuevo — diseño completo)
Propósito: verificación periódica de que la memoria acumulada sigue siendo cierta respecto al código real. Es el único rescate de BEMYAGENT. Se invoca explícitamente: "ejecutá AUDIT_DRIFT.md". Frecuencia sugerida: al cerrar una fase mayor, o ~mensual.

AUDIT DE DRIFT (invocación explícita del usuario — nunca automático)
Compará la memoria documentada contra la realidad del código. Reportá solo DESAJUSTES, no confirmaciones — lo que está bien no necesita mención.

Verificaciones (en orden, reportá al final en un solo bloque)
tech_stack.md vs realidad: ¿las dependencias listadas siguen siendo las del manifest real (pyproject.toml / package.json / etc.)? ¿Apareció alguna lib nueva no registrada en "Protocolos Críticos" que merezca regla?
roadmap.md vs git log: ¿las fases marcadas ✅ corresponden a work realmente mergeado? ¿Hay commits que impliquen avance de fase no reflejado?
lessons_learned.md vs código: tomá las 3 reglas de oro más recientes y verificá con grep/graphify que el patrón que prohíben no aparece violado en el código actual.
graphify: leé graphify-out/GRAPH_REPORT.md. ¿Hay god nodes nuevos, comunidades que se fusionaron, o conexiones sorprendentes que contradigan supuestos de architecture asumidos en sesiones previas?
observations.md: ¿alguna observación "en curso" ya quedó resuelta por código existente y debería moverse a archive + regla de oro?
Cobertura de .gitignore: ¿graphify-out/ y artefactos de build siguen ignorados? ¿Se acumulan archivos no versionados que deberían estarlo?

Formato del reporte
Por cada desajuste: [archivo de memoria] dice X / realidad dice Y / acción sugerida (una línea). Cerrá con: total de desajustes y si requieren actualización de memoria ya (protocolo de salida) o pueden esperar al cierre de sesión.

Nota de diseño: el audit reporta, no corrige. Las correcciones van por PROTOCOLO_SALIDA normal o por decisión del usuario. Esto mantiene la separación: el audit es diagnóstico, el protocolo es tratamiento.

5. Especificación de templates — archivos de memoria
Los 9 archivos se instalan con estructura completa y contenido vacío. Regla general: cada archivo lleva su header con su regla de rotación/ciclo de vida (para que el agente que lo lee por primera vez sepa cómo se mantiene), sus secciones, y nada más.

5.1 INDEX.md
INDEX — Mapa de Memoria
Leé esto SIEMPRE primero. Es corto a propósito.

Estado del proyecto
Proyecto: {{PROYECTO}}
Fase actual: 0
Próxima fase: 1 — [poblar en BOOTSTRAP]

Tabla de archivos
Archivo	Cuándo leerlo
INDEX.md	Siempre, primero
session_log.md	Siempre
lessons_learned.md	Siempre
tech_stack.md	Siempre
roadmap.md	Siempre
observations.md	Siempre
*_archive.md	Nunca automático — grep puntual si la tarea toca fase vieja
BOOTSTRAP.md	Solo la primera vez (invocación explícita del usuario)
AUDIT_DRIFT.md	Solo bajo invocación explícita del usuario (~mensual)

Convenciones
[3-4 líneas: regla de rotación de session_log (1 en detalle), lessons (últimas 2 fases), referencias cruzadas por número de regla]

5.2 Los archivos de memoria — estructura mínima por uno

| Archivo | Header debe contener | Secciones vacías |
|---------|---------------------|------------------|
| `session_log.md` | Regla de rotación (1 sesión detalle, resto comprimido, límite ~150-200 líneas) | `## ÚLTIMA SESIÓN` / `## HISTORIAL RELEVANTE` |
| `session_log_archive.md` | "Detalle completo verbatim de sesiones pasadas. No se lee automático." | `## Archivo de sesiones` |
| `lessons_learned.md` | Regla de rotación (últimas 2 fases; formato X.Y con Regla de Oro) | `## Índice de reglas archivadas` / `## Reglas activas` |
| `lessons_learned_archive.md` | "Reglas verbatim de fases rotadas. No se lee automático." | `## Archivo de reglas` |
| `tech_stack.md` | Nota: "Protocolos Críticos solo para invariantes que costó aprender — no transcribir el spec" | `## Stack Actual` / `## Protocolos Críticos` |
| `roadmap.md` | Nota: "Estado (✅/[ ]) + referencia. Detalle vive en lessons/session_log" | `## Fases` (lista numerada vacía) |
| `observations.md` | Regla de ciclo de vida (resuelta → archive + línea de cierre apuntando a Regla de Oro) | `## En curso` |
| `observations_archive.md` | "Observaciones cerradas verbatim. No se lee automático." | `## Archivo de observaciones` |

Los headers de cada archivo son copy exacta de las reglas que ya viven en tus protocolos actuales — GLM debe tomarlas de ahí, no reescribirlas. La fuente es tu PROTOCOLO_SALIDA.md y tus archivos reales del proyecto GND (que el usuario proveerá como material de referencia).

5.3 Validación de templates (para tests)
Cada template renderiza sin placeholders residuales (regex \{\{[A-Z_]+\}\} post-render → debe dar vacío).
Los 4 archivos de sistema contienen ambos marcadores scaffold:system (abierto y cerrado, en orden).
Los 9 de memoria no contienen ningún marcador.
Todos terminan en newline.

6. Fases de implementación (entregar a GLM así, con DoD por fase)

Fase 0 — Repo y esqueleto
Crear repo privado GitHub, estructura de carpetas de §2.1, .gitattributes, README (filosofía + flujo de uso en 5 pasos).
DoD: repo clonable, python3 bootstrap.py --help responde (aunque falle después).

Fase 1 — Templates
Los 13 archivos de templates/ con contenido final según §4 y §5.
DoD: revisión manual del usuario contra sus protocolos originales — cero divergencia no intencional. Los cambios intencionales son exactamente los listados en §4.2 (2), §4.3 (1) y el rediseño §4.1.

Fase 2 — Script
bootstrap.py completo según §3, con los 3 archivos de tests de §2.1.
DoD: test suite verde; corrida end-to-end en un repo sandbox (estructura creada, placeholders sustituidos, re-corrida entra en verify sin tocar nada, --force protege memoria con contenido).

Fase 3 — Validación en condiciones reales
Bootstrapear un proyecto real nuevo de punta a punta: script → GLM ejecuta BOOTSTRAP → una sesión normal con INICIO/SALIDA → un audit de drift.
DoD: el usuario confirma que el flujo reemplaza su proceso manual actual sin pérdidas.

Fase 4 — Implementada
--upgrade: reemplaza solo bloques scaffold:system en destinos existentes. Semántica exacta:
  (a) sistema con marcadores → reemplaza el bloque;
  (b) sistema sin marcadores → skip + reporta "legacy: migrar manualmente (borrar el archivo y
      re-correr --upgrade lo instala con marcadores)";
  (c) sistema ausente → se crea desde template (aditivo, consistente con §3.4).
  --force NO gana la capacidad de pisar sistemas sin marcadores (su semántica sigue siendo §3.5).
  Los 9 archivos de memoria nunca se tocan (invariante). Soporta --dry-run y --verbose.
Recordatorio en AGENTS.md/CLAUDE.md: DESCARTADO por decisión del usuario. El contexto se carga
manualmente al abrir sesión ("lee .agent/memory/PROTOCOLO_INICIO.md") para verificar que el modelo
realmente tiene contexto; no se auto-modifica el flujo hacia opencode/claude/codex.

7. Riesgos y notas de mantenibilidad
| Riesgo | Mitigación |
|--------|-----------|
| Drift entre plantilla y protocolos que el usuario mejora ad-hoc en un proyecto | El principio: mejoras a protocolos se hacen en la plantilla y se propagan; los proyectos viejos quedan en su versión (historia estable). |
| GLM "mejora" los templates durante Fase 1 inventando contenido | Instrucción dura en el prompt: los templates son copy de las fuentes provistas + cambios listados; nada se redacta de cero salvo AUDIT_DRIFT. |
| Script crece en features (config, idiomas, plugins) | Rechazo explícito: la plantilla es opinionada para un usuario. Toda feature nueva pasa por discusión de diseño primero. |
| Windows paths / encoding | pathlib en todo el script, UTF-8 explícito en cada open(), tests con nombres de archivo con espacios. |

8. Material que debes pasarle a GLM junto con este plan
Este documento.
2. Los 3 protocolos actuales del usuario (BOOTSTRAP, INICIO, SALIDA) — fuente para Fase 1.
3. Los archivos reales de memoria del proyecto GND (lessons_learned.md, observations.md + idealmente INDEX.md, session_log.md, tech_stack.md, roadmap.md de ese proyecto) — referencia de estructura madura para los templates vacíos.

Fin del documento.