import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.values = {"FECHA": "2026-08-19", "PROYECTO": "testproj", "AUTOR": "unknown"}

    def render(self, name, is_system):
        subdir = "system" if is_system else "memory"
        template_path = bootstrap.TEMPLATES_DIR / subdir / name
        return bootstrap.render_file(template_path, is_system, self.values)

    def test_all_templates_render_without_residual_placeholders(self):
        for name in bootstrap.ALL_FILES:
            is_system = name in bootstrap.SYSTEM_FILES
            rendered = self.render(name, is_system)
            self.assertFalse(
                re.search(r"\{\{[A-Z_]+\}\}", rendered),
                "%s dejó placeholders residuales" % name,
            )

    def test_system_templates_contain_markers_in_order(self):
        for name in bootstrap.SYSTEM_FILES:
            rendered = self.render(name, True)
            self.assertIn(bootstrap.MARKER_START, rendered, name)
            self.assertIn(bootstrap.MARKER_END, rendered, name)
            self.assertLess(
                rendered.index(bootstrap.MARKER_START),
                rendered.index(bootstrap.MARKER_END),
                name,
            )

    def test_memory_templates_have_no_markers(self):
        for name in bootstrap.MEMORY_FILES:
            rendered = self.render(name, False)
            self.assertNotIn(bootstrap.MARKER_START, rendered, name)
            self.assertNotIn(bootstrap.MARKER_END, rendered, name)

    def test_all_templates_end_with_newline(self):
        for name in bootstrap.ALL_FILES:
            is_system = name in bootstrap.SYSTEM_FILES
            self.assertTrue(self.render(name, is_system).endswith("\n"), name)

    def test_placeholder_substitution(self):
        content = "{{FECHA}}|{{PROYECTO}}|{{AUTOR}}"
        self.assertEqual(
            bootstrap.render_template(content, self.values),
            "2026-08-19|testproj|unknown",
        )

    def test_unknown_placeholder_raises(self):
        with self.assertRaises(ValueError):
            bootstrap.render_template("{{FOO}}", self.values)

    def test_render_file_raises_on_unknown_placeholder(self):
        template_path = Path(__file__).resolve().parent / "broken_template.md"
        template_path.write_text("{{DESCONOCIDO}}\n", encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                bootstrap.render_file(template_path, False, self.values)
        finally:
            template_path.unlink()

    def test_wrap_markers_idempotent(self):
        content = "una linea\n"
        once = bootstrap.wrap_markers(content, True)
        twice = bootstrap.wrap_markers(once, True)
        self.assertEqual(once, twice)
        self.assertEqual(once.count(bootstrap.MARKER_START), 1)
        self.assertEqual(once.count(bootstrap.MARKER_END), 1)

    def test_wrap_markers_skipped_for_memory(self):
        content = "una linea\n"
        self.assertEqual(bootstrap.wrap_markers(content, False), content)

    def test_protocolo_salida_has_session_identity_line(self):
        rendered = self.render("PROTOCOLO_SALIDA.md", True)
        self.assertIn("Sesión N — 2026-08-19", rendered)
        self.assertIn("vía OpenCode", rendered)


if __name__ == "__main__":
    unittest.main()