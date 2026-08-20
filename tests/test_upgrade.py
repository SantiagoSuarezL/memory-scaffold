import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap


def inject_inside_markers(path, line):
    text = path.read_text(encoding="utf-8")
    idx = text.index(bootstrap.MARKER_START) + len(bootstrap.MARKER_START)
    path.write_text(text[:idx] + "\n" + line + text[idx:], encoding="utf-8")


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scaffold upgrade ")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.project = Path(self.tmp) / "sandbox"
        self.project.mkdir()

    def run_main(self, *extra):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = bootstrap.main(["--project", str(self.project)] + list(extra))
        return code, buffer.getvalue()

    def memory(self):
        return self.project / ".agent" / "memory"

    def test_upgrade_replaces_system_blocks_only(self):
        self.run_main()
        target = self.memory() / "BOOTSTRAP.md"
        injected = "LÍNEA INYECTADA POR EL USUARIO"
        inject_inside_markers(target, injected)
        code, _ = self.run_main("--upgrade")
        self.assertEqual(code, 0)
        text = target.read_text(encoding="utf-8")
        self.assertNotIn(injected, text)
        self.assertIn(bootstrap.MARKER_START, text)
        self.assertIn(bootstrap.MARKER_END, text)

    def test_upgrade_creates_missing_system_file(self):
        self.run_main()
        target = self.memory() / "AUDIT_DRIFT.md"
        target.unlink()
        code, out = self.run_main("--upgrade")
        self.assertEqual(code, 0)
        self.assertTrue(target.exists())
        self.assertIn("Creados", out)
        self.assertIn("AUDIT_DRIFT.md", out)

    def test_upgrade_skips_legacy_without_markers(self):
        self.run_main()
        target = self.memory() / "BOOTSTRAP.md"
        legacy = "# bootstrap legacy sin marcadores\n"
        target.write_text(legacy, encoding="utf-8")
        code, out = self.run_main("--upgrade")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), legacy)
        self.assertIn("Legacy", out)

    def test_upgrade_never_touches_memory(self):
        self.run_main()
        target = self.memory() / "tech_stack.md"
        user_content = "# stack del usuario\n"
        target.write_text(user_content, encoding="utf-8")
        code, _ = self.run_main("--upgrade")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), user_content)

    def test_upgrade_force_does_not_acquire_legacy_overwrite(self):
        self.run_main()
        target = self.memory() / "PROTOCOLO_INICIO.md"
        legacy = "# inicio legacy sin marcadores\n"
        target.write_text(legacy, encoding="utf-8")
        code, out = self.run_main("--upgrade", "--force")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), legacy)
        self.assertIn("Legacy", out)

    def test_upgrade_dry_run_writes_nothing(self):
        self.run_main()
        target = self.memory() / "PROTOCOLO_SALIDA.md"
        injected = "LÍNEA DRY RUN"
        inject_inside_markers(target, injected)
        code, _ = self.run_main("--upgrade", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn(injected, target.read_text(encoding="utf-8"))

    def test_upgrade_without_install_errors(self):
        code = bootstrap.main(["--project", str(self.project), "--upgrade"])
        self.assertEqual(code, 1)

    def test_upgrade_with_markers_reports_unchanged_when_identical(self):
        self.run_main()
        code, out = self.run_main("--upgrade")
        self.assertEqual(code, 0)
        self.assertIn("Sin cambios", out)

    def test_extract_and_replace_block_roundtrip(self):
        content = "%s\n# titulo\ncuerpo\n%s\n" % (bootstrap.MARKER_START, bootstrap.MARKER_END)
        block = bootstrap.extract_block(content)
        self.assertEqual(block, "\n# titulo\ncuerpo\n")
        replaced = bootstrap.replace_block(content, "NUEVO")
        self.assertEqual(replaced, "%sNUEVO%s\n" % (bootstrap.MARKER_START, bootstrap.MARKER_END))


if __name__ == "__main__":
    unittest.main()