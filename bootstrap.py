#!/usr/bin/env python3
import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

SYSTEM_FILES = [
    "PROTOCOLO_INICIO.md",
    "PROTOCOLO_SALIDA.md",
    "BOOTSTRAP.md",
    "AUDIT_DRIFT.md",
]

MEMORY_FILES = [
    "INDEX.md",
    "session_log.md",
    "session_log_archive.md",
    "lessons_learned.md",
    "lessons_learned_archive.md",
    "tech_stack.md",
    "roadmap.md",
    "observations.md",
    "observations_archive.md",
]

ALL_FILES = ["INDEX.md"] + SYSTEM_FILES + [name for name in MEMORY_FILES if name != "INDEX.md"]

MARKER_START = "<!-- scaffold:system:start -->"
MARKER_END = "<!-- scaffold:system:end -->"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
MIN_PYTHON = (3, 8)


class BootstrapError(Exception):
    pass


def check_python_version(version=None):
    if (version or sys.version_info) < MIN_PYTHON:
        raise BootstrapError("Python >= 3.8 requerido para memory-scaffold.")


def git_user_name(project_dir):
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        name = result.stdout.strip()
        return name if name else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def placeholder_values(project_dir):
    return {
        "FECHA": datetime.date.today().isoformat(),
        "PROYECTO": Path(project_dir).name,
        "AUTOR": git_user_name(project_dir),
    }


def render_template(content, values):
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise ValueError("placeholder desconocido en template: {{%s}}" % key)
        return values[key]

    return PLACEHOLDER_RE.sub(replace, content)


def wrap_markers(content, is_system):
    if not is_system:
        return content
    lines = [
        line
        for line in content.splitlines()
        if line.strip() not in (MARKER_START, MARKER_END)
    ]
    body = "\n".join(lines).rstrip("\n")
    return "%s\n%s\n%s\n" % (MARKER_START, body, MARKER_END)


def extract_block(content):
    start = content.find(MARKER_START)
    end = content.find(MARKER_END, start)
    if start == -1 or end == -1:
        raise ValueError("no se encontraron ambos marcadores scaffold:system")
    return content[start + len(MARKER_START):end]


def replace_block(content, new_block):
    start = content.find(MARKER_START)
    end = content.find(MARKER_END, start)
    if start == -1 or end == -1:
        raise ValueError("no se encontraron ambos marcadores scaffold:system")
    return content[:start + len(MARKER_START)] + new_block + content[end:]


def render_file(template_path, is_system, values):
    content = template_path.read_text(encoding="utf-8")
    content = render_template(content, values)
    content = wrap_markers(content, is_system)
    if not content.endswith("\n"):
        content += "\n"
    return content


def validate_project(project):
    path = Path(project).expanduser()
    if not path.exists():
        raise BootstrapError("El destino no existe: %s" % path)
    if not path.is_dir():
        raise BootstrapError("El destino no es un directorio: %s" % path)
    if not os.access(path, os.W_OK):
        raise BootstrapError("El destino no tiene permisos de escritura: %s" % path)
    return path


def is_git_repo(project_dir):
    return (project_dir / ".git").exists()


def env_warnings(project_dir, templates_dir):
    warnings_list = []
    if not (project_dir / "docs").is_dir():
        warnings_list.append("docs/ no existe en el destino: BOOTSTRAP.md no tendrá specs que leer al poblar.")
    if not is_git_repo(project_dir):
        warnings_list.append("El destino no es un repo git: se recomienda git init antes del primer commit de memoria.")
    if project_dir.resolve() == templates_dir.parent.resolve():
        warnings_list.append("El destino es la propia plantilla: parece que estás bootstrapeando la plantilla en sí misma.")
    return warnings_list


def confirm(prompt):
    if not sys.stdin.isatty():
        return False
    try:
        answer = input("%s [s/N] " % prompt).strip().lower()
    except EOFError:
        return False
    return answer in ("s", "si", "y", "yes")


def plan_files(templates_dir, values):
    plan = []
    for name in ALL_FILES:
        is_system = name in SYSTEM_FILES
        subdir = "system" if is_system else "memory"
        template_path = templates_dir / subdir / name
        rendered = render_file(template_path, is_system, values)
        plan.append((name, rendered, is_system))
    return plan


def file_status(rendered, target_path, filename):
    if not target_path.exists():
        return "falta"
    if target_path.read_text(encoding="utf-8") == rendered:
        return "ok"
    if filename in MEMORY_FILES:
        return "memoria-protegida"
    return "difiere"


def print_tree(plan, memory_dir):
    print("Estructura creada en %s" % memory_dir)
    print(".agent/")
    print("`-- memory/")
    for index, (name, _, _) in enumerate(plan):
        branch = "|-- " if index < len(plan) - 1 else "`-- "
        print("    %s%s" % (branch, name))


def print_warnings(project_dir, templates_dir):
    warnings_list = env_warnings(project_dir, templates_dir)
    if warnings_list:
        print("")
        print("Warnings:")
        for warning in warnings_list:
            print(" - %s" % warning)


def print_install_plan(plan, memory_dir):
    print("Plan (--dry-run — no se escribe nada):")
    for name, _, _ in plan:
        print("  crear   %s" % (memory_dir / name))


def print_verify_report(statuses, memory_dir):
    missing = [s for s in statuses if s[3] == "falta"]
    ok = [s for s in statuses if s[3] == "ok"]
    protected = [s for s in statuses if s[3] == "memoria-protegida"]
    differ = [s for s in statuses if s[3] == "difiere"]

    print("%s ya existe (modo verify — no se modifica nada)." % memory_dir)
    if missing:
        print("Faltan %d archivos:" % len(missing))
        for name, _, _, _ in missing:
            print("  - %s" % name)
    if protected:
        print("Protegidos (memoria con contenido):")
        for name, _, _, _ in protected:
            print("  - %s" % name)
    if differ:
        print("Difieren del template (archivos de sistema):")
        for name, _, _, _ in differ:
            target = memory_dir / name
            text = target.read_text(encoding="utf-8")
            note = (
                "con marcadores scaffold (instalación moderna)"
                if MARKER_START in text and MARKER_END in text
                else "sin marcadores scaffold (instalación manual antigua)"
            )
            print("  - %s (%s)" % (name, note))
    if ok:
        print("%d archivos ya coinciden con el template." % len(ok))
    print("")
    print("Sugerencia: faltan %d archivos; corre con --force para completar, o --dry-run para ver el plan." % len(missing))


def print_force_plan(statuses, memory_dir):
    print("Plan (--dry-run + --force):")
    for name, _, _, status in statuses:
        if status == "falta":
            print("  crear      %s" % (memory_dir / name))
        elif status == "ok":
            print("  sin cambio %s" % (memory_dir / name))
        elif status == "difiere":
            print("  sobrescribiría (requiere confirmación) %s" % (memory_dir / name))
        elif status == "memoria-protegida":
            print("  protegido (memoria con contenido) %s" % (memory_dir / name))


def run_install(project_dir, templates_dir, args):
    memory_dir = project_dir / ".agent" / "memory"
    values = placeholder_values(project_dir)
    plan = plan_files(templates_dir, values)

    if args.dry_run:
        print_install_plan(plan, memory_dir)
        print_warnings(project_dir, templates_dir)
        return 0

    memory_dir.mkdir(parents=True, exist_ok=True)
    for name, rendered, _ in plan:
        target = memory_dir / name
        target.write_text(rendered, encoding="utf-8", newline="\n")
        if args.verbose:
            print("  creando %s" % target)

    print_tree(plan, memory_dir)
    print("")
    print("Placeholders sustituidos: %s" % ", ".join(sorted(values)))
    print_warnings(project_dir, templates_dir)
    return 0


def run_existing(project_dir, templates_dir, args):
    memory_dir = project_dir / ".agent" / "memory"
    values = placeholder_values(project_dir)
    plan = plan_files(templates_dir, values)

    statuses = []
    for name, rendered, is_system in plan:
        target = memory_dir / name
        statuses.append((name, rendered, is_system, file_status(rendered, target, name)))

    if not args.force:
        print_verify_report(statuses, memory_dir)
        return 0

    if args.dry_run:
        print_force_plan(statuses, memory_dir)
        return 0

    for name, rendered, _, status in statuses:
        target = memory_dir / name
        if status == "falta":
            target.write_text(rendered, encoding="utf-8", newline="\n")
            if args.verbose:
                print("  creando %s" % target)
        elif status == "difiere":
            if confirm("¿Sobrescribir %s (difiere del template)?" % name):
                target.write_text(rendered, encoding="utf-8", newline="\n")
                if args.verbose:
                    print("  sobrescribiendo %s" % target)
            else:
                print("  protegido: %s" % name)
        elif status == "memoria-protegida":
            print("  protegido (memoria con contenido): %s" % name)
    return 0


def run_upgrade(project_dir, templates_dir, args):
    memory_dir = project_dir / ".agent" / "memory"
    values = placeholder_values(project_dir)
    plan = plan_files(templates_dir, values)

    created = []
    replaced = []
    unchanged = []
    legacy = []

    for name, rendered, is_system in plan:
        if not is_system:
            continue
        target = memory_dir / name
        if not target.exists():
            created.append(name)
            if not args.dry_run:
                target.write_text(rendered, encoding="utf-8", newline="\n")
                if args.verbose:
                    print("  creando %s" % target)
            continue
        text = target.read_text(encoding="utf-8")
        if MARKER_START not in text or MARKER_END not in text:
            legacy.append(name)
            continue
        updated = replace_block(text, extract_block(rendered))
        if updated == text:
            unchanged.append(name)
            continue
        replaced.append(name)
        if not args.dry_run:
            target.write_text(updated, encoding="utf-8", newline="\n")
            if args.verbose:
                print("  reemplazando bloque de %s" % target)

    print("Upgrade de archivos de sistema en %s" % memory_dir)
    if created:
        print("Creados (no existían):")
        for name in created:
            print("  + %s" % name)
    if replaced:
        print("Bloque scaffold actualizado:")
        for name in replaced:
            print("  ~ %s" % name)
    if unchanged:
        print("Sin cambios (%d): %s" % (len(unchanged), ", ".join(unchanged)))
    if legacy:
        print("Legacy — migrar manualmente (borrar el archivo y re-correr --upgrade para instalarlo con marcadores):")
        for name in legacy:
            print("  ! %s" % name)
    if args.dry_run:
        print("(--dry-run: no se escribió nada)")
    print("Los 9 archivos de memoria no se tocaron (invariante).")
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="memory-scaffold: instala la estructura de memoria para agentes en un proyecto destino.",
    )
    parser.add_argument("--project", default=".", help="Directorio destino (default: directorio actual).")
    parser.add_argument("--force", action="store_true", help="Completa instalaciones parciales; jamás pisa memoria con contenido.")
    parser.add_argument("--dry-run", action="store_true", help="Muestra qué haría sin escribir nada.")
    parser.add_argument("--verbose", action="store_true", help="Log detallado de cada archivo procesado.")
    parser.add_argument("--upgrade", action="store_true", help="Reemplaza solo los bloques scaffold:system de los archivos de sistema en destinos existentes (no toca memoria).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        check_python_version()
        project_dir = validate_project(args.project)
        memory_dir = project_dir / ".agent" / "memory"
        if args.upgrade:
            if not memory_dir.is_dir():
                raise BootstrapError("No hay instalación previa en el destino; corré sin --upgrade para instalar.")
            return run_upgrade(project_dir, TEMPLATES_DIR, args)
        if memory_dir.is_dir():
            return run_existing(project_dir, TEMPLATES_DIR, args)
        return run_install(project_dir, TEMPLATES_DIR, args)
    except BootstrapError as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print("Error en template: %s" % exc, file=sys.stderr)
        return 1
    except OSError as exc:
        print("Error de I/O: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())