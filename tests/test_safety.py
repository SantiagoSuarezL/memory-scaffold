import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scaffold safety ")
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

    def test_memory_file_always_protected_with_force(self):
        self.run_main()
        target = self.memory() / "tech_stack.md"
        user_content = "# contenido del usuario\n"
        target.write_text(user_content, encoding="utf-8")
        code, out = self.run_main("--force")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), user_content)
        self.assertIn("memoria con contenido", out)

    def test_system_file_protected_without_interactive_confirm(self):
        self.run_main()
        target = self.memory() / "BOOTSTRAP.md"
        user_content = "# bootstrap editado por el usuario\n"
        target.write_text(user_content, encoding="utf-8")
        code, out = self.run_main("--force")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), user_content)

    def test_force_does_not_touch_identical_memory(self):
        self.run_main()
        target = self.memory() / "observations.md"
        original = target.read_text(encoding="utf-8")
        code, _ = self.run_main("--force")
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_dry_run_force_reports_protected_vs_overwrite(self):
        self.run_main()
        memory_target = self.memory() / "observations.md"
        memory_target.write_text("# obs del usuario\n", encoding="utf-8")
        system_target = self.memory() / "AUDIT_DRIFT.md"
        system_target.write_text("# audit editado\n", encoding="utf-8")
        code, out = self.run_main("--force", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("protegido (memoria con contenido)", out)
        self.assertIn("sobrescribiría", out)
        self.assertEqual(memory_target.read_text(encoding="utf-8"), "# obs del usuario\n")
        self.assertEqual(system_target.read_text(encoding="utf-8"), "# audit editado\n")

    def test_dest_missing_returns_1(self):
        missing = self.project / "no-existe"
        code = bootstrap.main(["--project", str(missing)])
        self.assertEqual(code, 1)

    def test_dest_is_file_returns_1(self):
        target = self.project / "archivo.txt"
        target.write_text("x", encoding="utf-8")
        code = bootstrap.main(["--project", str(target)])
        self.assertEqual(code, 1)

    def test_python_version_check(self):
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.check_python_version((3, 7))
        bootstrap.check_python_version((3, 8))

    def test_render_unknown_placeholder_fails_install_pipeline(self):
        template_path = self.project / "broken.md"
        template_path.write_text("{{DESCONOCIDO}}\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            bootstrap.render_file(
                template_path,
                False,
                {"FECHA": "x", "PROYECTO": "x", "AUTOR": "x"},
            )

    def test_second_install_is_verify_and_does_not_change(self):
        self.run_main()
        memory = self.memory()
        before = {p.name: p.read_text(encoding="utf-8") for p in memory.glob("*")}
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("modo verify", out)
        after = {p.name: p.read_text(encoding="utf-8") for p in memory.glob("*")}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()