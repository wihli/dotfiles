#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "bin/.local/bin/agent-aws-prod-guard"


class AgentAwsProdGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.config_home = self.root / "config"
        self.cache_home = self.root / "cache"
        self.state_home = self.root / "state"
        self.home.mkdir()
        (self.config_home / "agent-aws-prod-guard").mkdir(parents=True)
        self.write_guard_config({})

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def base_env(self) -> dict[str, str]:
        return {
            **os.environ,
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.config_home),
            "XDG_CACHE_HOME": str(self.cache_home),
            "XDG_STATE_HOME": str(self.state_home),
            "PATH": os.environ.get("PATH", ""),
        }

    def write_guard_config(self, extra: dict[str, object]) -> None:
        config = {
            "production_account_ids": ["123456789012"],
            "non_production_account_ids": ["210987654321"],
            "production_profile_patterns": ["prod", "*-prod", "*prod*"],
            "safe_profile_patterns": ["staging", "*staging*", "sandbox"],
            "cache_ttl_seconds": 900,
        }
        config.update(extra)
        path = self.config_home / "agent-aws-prod-guard/config.json"
        path.write_text(json.dumps(config))

    def run_hook(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        tool_name: str = "Bash",
    ) -> subprocess.CompletedProcess[str]:
        payload = {"tool_name": tool_name, "tool_input": {"command": command}}
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--agent", "test"],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**self.base_env(), **(env or {})},
            check=False,
        )

    def test_blocks_risky_command_when_profile_name_is_prod(self) -> None:
        result = self.run_hook("aws s3 ls", env={"AWS_PROFILE": "prod"})

        self.assertEqual(result.returncode, 2)
        output = json.loads(result.stdout)
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("production profile pattern", output["permissionDecisionReason"])

    def test_allows_risky_command_when_profile_name_is_safe(self) -> None:
        result = self.run_hook("terraform plan", env={"AWS_PROFILE": "staging"})

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_allows_configured_safe_command_even_when_prod(self) -> None:
        result = self.run_hook(
            "DD_SITE=ddog-gov.com pup logs search 'env:prod'",
            env={"AWS_PROFILE": "prod"},
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_safe_command_prefix_does_not_allow_command_chain(self) -> None:
        result = self.run_hook(
            "pup logs search 'env:prod' && aws s3 ls",
            env={"AWS_PROFILE": "prod"},
        )

        self.assertEqual(result.returncode, 2)
        output = json.loads(result.stdout)
        self.assertEqual(output["permissionDecision"], "deny")

    def test_blocks_prod_profile_selected_inside_command(self) -> None:
        result = self.run_hook("aws-vault exec prod -- terraform plan")

        self.assertEqual(result.returncode, 2)
        output = json.loads(result.stdout)
        self.assertEqual(output["permissionDecision"], "deny")

    def test_uses_sts_cache_for_ambiguous_risky_command(self) -> None:
        counter = self.root / "sts-count"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        aws = bin_dir / "aws"
        aws.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                echo call >> {counter}
                printf '%s\\n' '{{"Account":"123456789012","Arn":"arn:aws:sts::123456789012:assumed-role/prod/test","UserId":"test"}}'
                """
            )
        )
        aws.chmod(0o755)
        env = {
            "AWS_PROFILE": "unknown",
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        }

        first = self.run_hook("python3 -c 'print(1)'", env=env)
        second = self.run_hook("python3 -c 'print(1)'", env=env)

        self.assertEqual(first.returncode, 2)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(counter.read_text().splitlines(), ["call"])

    def test_ignores_non_command_tool(self) -> None:
        result = self.run_hook("", tool_name="Read", env={"AWS_PROFILE": "prod"})

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
