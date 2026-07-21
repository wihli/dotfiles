from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bin/.local/bin/codex-recap"


def load_script():
    loader = SourceFileLoader("codex_recap", str(SCRIPT_PATH))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


class CodexRecapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recap = load_script()

    def test_non_recap_prompt_is_ignored(self) -> None:
        def unexpected_runner(*args, **kwargs):
            self.fail("summarizer should not run for an ordinary prompt")

        result = self.recap.process_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "keep working",
                "session_id": "session-123",
            },
            runner=unexpected_runner,
        )

        self.assertIsNone(result)

    def test_recap_prompt_uses_ephemeral_mini_model(self) -> None:
        calls = []

        def fake_runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="Goal: recover context\nCurrent state: ready",
                stderr="",
            )

        result = self.recap.process_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "  ReCaP  ",
                "session_id": "session-123",
            },
            runner=fake_runner,
        )

        command, kwargs = calls[0]
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("hooks", command)
        self.assertEqual(command[command.index("--model") + 1], "gpt-5.4-mini")
        self.assertEqual(command[command.index("resume") + 1], "session-123")
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])
        self.assertFalse(result["continue"])
        self.assertEqual(
            result["systemMessage"],
            "Goal: recover context\nCurrent state: ready",
        )

    def test_summarizer_failure_is_explicit(self) -> None:
        def failing_runner(command, **kwargs):
            return subprocess.CompletedProcess(
                command, 1, stdout="", stderr="model unavailable"
            )

        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            self.recap.generate_recap("session-123", runner=failing_runner)

    def test_missing_session_id_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "session ID"):
            self.recap.resolve_session_id(None, {})

    def test_codex_user_prompt_hook_invokes_recap_command(self) -> None:
        hooks_path = REPO_ROOT / "codex/.codex/hooks.json"
        hooks = json.loads(hooks_path.read_text())
        commands = [
            hook["command"]
            for group in hooks["hooks"]["UserPromptSubmit"]
            for hook in group["hooks"]
        ]

        self.assertIn("codex-recap --hook", commands)


if __name__ == "__main__":
    unittest.main()
