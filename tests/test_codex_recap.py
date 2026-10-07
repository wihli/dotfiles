from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import subprocess
import tempfile
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

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "rollout-session-123.jsonl"
            transcript_path.write_text(
                json.dumps(
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "Fix it."}],
                        },
                    }
                )
                + "\n"
            )
            result = self.recap.process_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "  ReCaP  ",
                    "session_id": "session-123",
                    "transcript_path": str(transcript_path),
                },
                runner=fake_runner,
            )

        command, kwargs = calls[0]
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("hooks", command)
        self.assertEqual(command[command.index("--model") + 1], "gpt-5.4-mini")
        self.assertNotIn("resume", command)
        self.assertEqual(command[-1], "-")
        self.assertIn("USER:\nFix it.", kwargs["input"])
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
            self.recap.generate_recap("USER:\nhello", runner=failing_runner)

    def test_missing_session_id_has_actionable_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "session ID"):
            self.recap.resolve_session_id(None, {})

    def test_resolve_transcript_path_uses_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = (
                Path(tmpdir)
                / "sessions/2026/08/25/rollout-example-session-123.jsonl"
            )
            transcript_path.parent.mkdir(parents=True)
            transcript_path.write_text("{}\n")

            result = self.recap.resolve_transcript_path(
                "session-123", {"CODEX_HOME": tmpdir}
            )

        self.assertEqual(result, transcript_path)

    def test_extract_conversation_ignores_instructions_and_tool_events(self) -> None:
        records = [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "secret rules"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Explain the failure"}],
                },
            },
            {
                "type": "response_item",
                "payload": {"type": "custom_tool_call_output", "output": "tool output"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "It is a lock conflict."}],
                },
            },
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "session.jsonl"
            transcript_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records)
            )

            conversation = self.recap.extract_conversation(transcript_path)

        self.assertEqual(
            conversation,
            "USER:\nExplain the failure\n\nASSISTANT:\nIt is a lock conflict.",
        )
        self.assertNotIn("secret rules", conversation)
        self.assertNotIn("tool output", conversation)

    def test_hook_requires_transcript_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "transcript_path"):
            self.recap.process_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "recap",
                    "session_id": "session-123",
                }
            )

    def test_extract_conversation_skips_context_codex_injects_as_user(self) -> None:
        # Codex records AGENTS.md and environment context as user messages. Left in,
        # they fill the truncation head and read to the recap model as user requests.
        texts = [
            "# AGENTS.md instructions for /repo\n\n<INSTRUCTIONS>rules</INSTRUCTIONS>",
            "<environment_context>\n  <cwd>/repo</cwd>\n</environment_context>",
            "Why does the export stall?",
        ]
        records = [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
            for text in texts
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "session.jsonl"
            transcript_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records)
            )

            conversation = self.recap.extract_conversation(transcript_path)

        self.assertEqual(conversation, "USER:\nWhy does the export stall?")

    def test_extract_conversation_rejects_non_object_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript_path = Path(tmpdir) / "session.jsonl"
            transcript_path.write_text("[]\n")

            with self.assertRaisesRegex(ValueError, "JSON object"):
                self.recap.extract_conversation(transcript_path)

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
