from pathlib import Path
import os
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "bin/.local/bin/agent-notify-ready"

FAKE_TMUX = """#!/bin/bash
case "$*" in
    *pane_active*) printf '%s' "${FAKE_TMUX_VISIBILITY:-000}" ;;
    *pane_title*) printf 'Old Title' ;;
    *session_name*) printf 'main:1.0 %%5' ;;
esac
exit 0
"""

FAKE_LSAPPINFO = """#!/bin/bash
[ -n "${FAKE_FRONT_BUNDLE:-}" ] || exit 1
case "$1" in
    front) printf 'ASN:0x0-0x1:\\n' ;;
    info) printf '"CFBundleIdentifier"="%s"\\n' "$FAKE_FRONT_BUNDLE" ;;
esac
"""

FAKE_NOTIFIER = """#!/bin/bash
printf '%s\\n' "$*" >> "$FAKE_NOTIFIER_CALLS"
exit 0
"""


class AgentNotifyReadyBannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, body in (("tmux", FAKE_TMUX), ("lsappinfo", FAKE_LSAPPINFO), ("terminal-notifier", FAKE_NOTIFIER)):
            path = self.root / name
            path.write_text(body)
            path.chmod(0o755)
        self.calls = self.root / "notifier-calls"
        self.state = self.root / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args, env=None, visibility="000", front=None, ready=None):
        environment = {
            "PATH": f"{self.root}:/usr/bin:/bin",
            "HOME": str(self.root),
            "XDG_STATE_HOME": str(self.state),
            "TMUX": "/tmp/tmux-test/default,1,0",
            "TMUX_PANE": "%5",
            "AGENT_NOTIFY_TERMINAL_BUNDLE": "com.mitchellh.ghostty",
            "FAKE_NOTIFIER_CALLS": str(self.calls),
            "FAKE_TMUX_VISIBILITY": visibility,
        }
        if front is not None:
            environment["FAKE_FRONT_BUNDLE"] = front
        if ready is not None:
            environment["AGENT_NOTIFY_READY"] = ready
        if env:
            environment.update(env)
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            env=environment,
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "", "hook stdout must stay empty")
        return result

    def banners(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def events(self):
        log = self.state / "agent-notify-ready" / "events.log"
        return log.read_text().splitlines() if log.exists() else []

    def test_banner_fires_when_terminal_is_not_frontmost(self):
        self.run_script("Claude Code", front="com.tinyspeck.slackmacgap", visibility="111")
        self.assertEqual(len(self.banners()), 1)
        self.assertIn("-title Claude Code ready", self.banners()[0])
        self.assertTrue(any(" event=notify " in line for line in self.events()))

    def test_banner_fires_when_pane_is_not_visible_in_frontmost_terminal(self):
        # Another tmux window or pane is active, so the ready marker is hidden.
        self.run_script("Claude Code", front="com.mitchellh.ghostty", visibility="011")
        self.assertEqual(len(self.banners()), 1)

    def test_no_banner_when_pane_is_on_screen(self):
        self.run_script("Claude Code", front="com.mitchellh.ghostty", visibility="112")
        self.assertEqual(self.banners(), [])
        self.assertTrue(any("event=notify-skip" in line and "detail=on-screen" in line for line in self.events()))
        # The READY title marker is still applied.
        self.assertTrue(any(" event=title " in line for line in self.events()))

    def test_banner_fires_when_frontmost_app_is_unknown(self):
        self.run_script("Claude Code", front=None, visibility="111")
        self.assertEqual(len(self.banners()), 1)

    def test_environment_switch_disables_banner(self):
        self.run_script("Claude Code", front="com.tinyspeck.slackmacgap", ready="off")
        self.assertEqual(self.banners(), [])
        self.assertTrue(any("detail=env" in line for line in self.events()))

    def test_mute_and_unmute_apply_to_the_current_pane(self):
        self.run_script("--mute")
        self.run_script("Claude Code", front="com.tinyspeck.slackmacgap")
        self.assertEqual(self.banners(), [], "muted pane must not banner")
        self.assertTrue(any("detail=muted" in line for line in self.events()))
        self.run_script("--unmute")
        self.run_script("Claude Code", front="com.tinyspeck.slackmacgap")
        self.assertEqual(len(self.banners()), 1)

    def test_mute_outside_tmux_is_recorded_and_harmless(self):
        env = {"TMUX": "", "TMUX_PANE": ""}
        self.run_script("--mute", env=env)
        self.assertTrue(any("event=mute-no-tmux" in line for line in self.events()))
        self.run_script("Claude Code", env=env, front="com.tinyspeck.slackmacgap")
        self.assertEqual(len(self.banners()), 1)


if __name__ == "__main__":
    unittest.main()
