from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexSkillPreferencesTests(unittest.TestCase):
    def run_merge(self, source, target):
        installer = (REPO_ROOT / 'install.sh').read_text()
        marker = "<<'PY_CODEX_SKILLS'\n"
        if marker not in installer:
            self.fail("Codex skill preference merger is missing")
        code = installer.split(marker, 1)[1].split('\nPY_CODEX_SKILLS', 1)[0]
        return subprocess.run([sys.executable, '-', str(source), str(target)],
                              input=code, text=True, capture_output=True)

    def test_preferences_preserve_user_settings_and_are_repeatable(self):
        # A synced skill preference must not replace model, permissions, or manual overrides.
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'skills.toml', Path(tmp) / 'config.toml'
            original = ('# User comment\nmodel = "chosen-model"\n'
                        '[features]\nexample = true\n'
                        '[[skills.config]]\nname = "other"\nenabled = false\n')
            target.write_text(original)
            target.chmod(0o600)
            source.write_text('[[skills.config]]\nname = "sales"\nenabled = false\n')
            result = self.run_merge(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            first = target.read_text()
            self.assertTrue(first.startswith(original))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            data = tomllib.loads(first)
            self.assertEqual(data['model'], 'chosen-model')
            self.assertEqual(data['features'], {'example': True})
            self.assertEqual(data['skills']['config'], [
                {'name': 'other', 'enabled': False}, {'name': 'sales', 'enabled': False}])
            self.assertEqual(self.run_merge(source, target).returncode, 0)
            self.assertEqual(target.read_text(), first)
            source.write_text('[[skills.config]]\nname = "sales"\nenabled = true\n')
            self.assertEqual(self.run_merge(source, target).returncode, 0)
            updated = tomllib.loads(target.read_text())['skills']['config']
            self.assertEqual(updated, [
                {'name': 'other', 'enabled': False}, {'name': 'sales', 'enabled': True}])
            source.write_text('')
            self.assertEqual(self.run_merge(source, target).returncode, 0)
            self.assertEqual(tomllib.loads(target.read_text())['skills']['config'],
                             [{'name': 'other', 'enabled': False}])

    def test_invalid_preferences_leave_existing_config_intact(self):
        invalid = [
            '[[skills.config]]\nname = "sales"\nenabled = "no"\n',
            '[[skills.config]]\nname = "sales"\npath = "/skill/SKILL.md"\nenabled = false\n',
            'model = "unexpected"\n',
            '[[skills.config]]\nname = ""\nenabled = false\n',
            'not valid toml',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'skills.toml', Path(tmp) / 'config.toml'
            for content in invalid:
                with self.subTest(content=content):
                    original = 'model = "chosen-model"\n'
                    target.write_text(original)
                    source.write_text(content)
                    self.assertNotEqual(self.run_merge(source, target).returncode, 0)
                    self.assertEqual(target.read_text(), original)

    def test_unfinished_managed_block_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'skills.toml', Path(tmp) / 'config.toml'
            original = '# BEGIN wihli-dotfiles skill preferences\nmodel = "keep"\n'
            target.write_text(original)
            source.write_text('[[skills.config]]\nname = "sales"\nenabled = false\n')
            self.assertNotEqual(self.run_merge(source, target).returncode, 0)
            self.assertEqual(target.read_text(), original)


if __name__ == '__main__':
    unittest.main()
