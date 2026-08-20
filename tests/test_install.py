import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scaffold test ")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.project = Path(self.tmp) / "mi proyecto"
        self.project.mkdir()

    def run_main(self, *extra):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = bootstrap.main(["--project", str(self.project)] + list(extra))
        return code, buffer.getvalue()

    def memory_files(self):
        memory = self.project / ".agent" / "memory"
        return sorted(p.name for p in memory.glob("*")) if memory.is_dir() else []

    def test_install_creates_13_files(self):
        code, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.memory_files()), 13)
        for name in bootstrap.ALL_FILES:
            self.assertIn(name, self.memory_files())

    def test_installed_index_has_project_name(self):
        self.run_main()
        index = self.project / ".agent" / "memory" / "INDEX.md"
        self.assertIn("mi proyecto", index.read_text(encoding="utf-8"))

    def test_installed_protocolo_salida_has_date_substituted(self):
        import datetime
        self.run_main()
        target = self.project / ".agent" / "memory" / "PROTOCOLO_SALIDA.md"
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("{{FECHA}}", text)
        self.assertIn(datetime.date.today().isoformat(), text)

    def test_dry_run_writes_nothing(self):
        code, out = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse((self.project / ".agent").exists())
        self.assertIn("crear", out)

    def test_install_when_agent_exists_without_memory(self):
        (self.project / ".agent").mkdir()
        code, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.memory_files()), 13)

    def test_verify_mode_reports_partial_without_changes(self):
        self.run_main()
        memory = self.project / ".agent" / "memory"
        for name in bootstrap.ALL_FILES[5:]:
            (memory / name).unlink()
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.memory_files()), 5)
        self.assertIn("Faltan 8", out)
        self.assertIn("--force", out)

    def test_force_completes_partial_install(self):
        self.run_main()
        memory = self.project / ".agent" / "memory"
        for name in bootstrap.ALL_FILES[5:]:
            (memory / name).unlink()
        code, _ = self.run_main("--force")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.memory_files()), 13)

    def test_paths_with_spaces_work(self):
        code, _ = self.run_main()
        self.assertEqual(code, 0)
        index = self.project / ".agent" / "memory" / "INDEX.md"
        self.assertIn("mi proyecto", index.read_text(encoding="utf-8"))

    def test_verbose_lists_files(self):
        code, out = self.run_main("--verbose")
        self.assertEqual(code, 0)
        self.assertIn("creando", out)

    def test_warns_when_bootstrapping_self(self):
        repo = bootstrap.TEMPLATES_DIR.parent
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = bootstrap.main(["--project", str(repo), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("la plantilla en sí misma", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()