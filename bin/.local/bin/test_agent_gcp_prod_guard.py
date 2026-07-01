"""Tests for agent-gcp-prod-guard.

Exercises the pure decide() core with an injected ambient resolver so no gcloud
subprocess runs. Mirrors the real private config: dev-env-430408 allowed,
production-432610 blocked, read-only + ambient enforcement on.

Run: python3 -m pytest test_agent_gcp_prod_guard.py
"""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).with_name("agent-gcp-prod-guard")
_loader = SourceFileLoader("agent_gcp_prod_guard", str(_MODULE_PATH))
_spec = importlib.util.spec_from_loader("agent_gcp_prod_guard", _loader)
guard = importlib.util.module_from_spec(_spec)
_loader.exec_module(guard)


BASE_CONFIG = {
    **guard.DEFAULT_CONFIG,
    "allowed_projects": ["dev-env-430408"],
    "blocked_projects": ["production-432610"],
}


def ambient(project=None, kube=None):
    return lambda _config: {"project": project, "kube_context": kube}


def decide(command, config=None, amb=None):
    config = config or BASE_CONFIG
    return guard.decide("Bash", command, config, ambient=amb or ambient())


def is_denied(command, **kw):
    return decide(command, **kw)[0] == "deny"


# --- allow: non-GCP and safe reads ---------------------------------------- #
def test_non_gcp_command_allowed():
    assert not is_denied("git status && ls -la")


def test_gcloud_read_on_dev_allowed():
    assert not is_denied("gcloud compute instances list --project dev-env-430408")


def test_kubectl_get_allowed_on_dev_context():
    assert not is_denied("kubectl get pods -n default", amb=ambient(kube="dev-gke"))


def test_meta_read_allowed_even_when_ambient_prod():
    # config get-value must work so an agent can discover its project
    assert not is_denied(
        "gcloud config get-value project", amb=ambient(project="production-432610")
    )


def test_gsutil_ls_on_dev_allowed():
    assert not is_denied("gsutil ls gs://my-bucket", amb=ambient(project="dev-env-430408"))


# --- deny: production references ------------------------------------------- #
def test_blocked_project_id_literal_denied():
    assert is_denied("gcloud compute instances list --project production-432610")


def test_prod_pattern_project_denied():
    assert is_denied("gcloud run services list --project acme-prod-123")


def test_ambient_prod_project_denied():
    assert is_denied(
        "gcloud compute instances list", amb=ambient(project="production-432610")
    )


def test_ambient_non_allowlisted_project_denied():
    assert is_denied(
        "gcloud storage buckets list", amb=ambient(project="some-other-project")
    )


def test_kube_prod_context_denied():
    assert is_denied("kubectl get pods", amb=ambient(kube="production-gke-cluster"))


# --- deny: mutations (read-only posture) ---------------------------------- #
@pytest.mark.parametrize("command", [
    "gcloud compute instances delete foo --project dev-env-430408",
    "gcloud projects add-iam-policy-binding dev-env-430408 --member=user:x --role=roles/owner",
    "gcloud auth print-access-token",
    "gcloud config set project dev-env-430408",
    "gsutil rm gs://dev-bucket/obj",
    "gsutil cat gs://dev-bucket/secret.txt",
    "bq query 'SELECT 1'",
    "kubectl delete pod foo",
    "kubectl apply -f deploy.yaml",
    "kubectl exec -it pod -- sh",
    "kubectl config view",
], ids=lambda c: c.split()[1])
def test_mutations_denied(command):
    assert is_denied(command, amb=ambient(project="dev-env-430408", kube="dev-gke"))


# --- compound commands & bypass attempts ---------------------------------- #
def test_safe_prefix_with_chained_mutation_denied():
    # "gcloud version" is a safe prefix, but a chained delete must still block
    assert is_denied(
        "gcloud version && gcloud compute instances delete foo --project dev-env-430408"
    )


def test_prod_reference_anywhere_in_pipeline_denied():
    assert is_denied("echo hi | gcloud compute ssh --project production-432610 vm")


# --- read_only disabled --------------------------------------------------- #
def test_mutation_allowed_when_read_only_disabled_on_dev():
    cfg = {**BASE_CONFIG, "read_only": False}
    assert not is_denied(
        "gcloud compute instances delete foo --project dev-env-430408",
        config=cfg,
        amb=ambient(project="dev-env-430408"),
    )
    # ...but prod is still blocked even with writes enabled
    cfg_amb = ambient(project="dev-env-430408")
    assert guard.decide(
        "Bash",
        "gcloud compute instances delete foo --project production-432610",
        cfg,
        ambient=cfg_amb,
    )[0] == "deny"


# --- command position: mentions must NOT trip; invocations must ------------ #
@pytest.mark.parametrize("command", [
    'git commit -m "delete stale gcloud cache"',
    'git commit -m "bump bq and gsutil helpers"',
    "grep -rn gcloud .",
    "grep -rn production-432610 .",
    'echo "run: gcloud compute instances delete foo"',
    "rg 'kubectl delete' notes.md",
    # `|` inside a quoted regex alternation must not read as a shell pipe:
    "grep -oE '(terraform|gcloud|kubectl|gsutil)' log.md",
    'jq -r ".cmd" run.json | grep gcloud',
], ids=lambda c: c[:26])
def test_mentions_are_not_invocations(command):
    # tools merely referenced in args/messages/patterns are never a gcp op,
    # even with a hostile ambient identity — the guard must not fire.
    assert not is_denied(command, amb=ambient(project="production-432610", kube="prod-gke"))


@pytest.mark.parametrize("command", [
    'zsh -lc "gcloud compute instances delete foo --project production-432610"',
    'bash -c "gcloud compute instances list --project production-432610"',
    "CLOUDSDK_CORE_PROJECT=production-432610 gcloud compute instances list",
    "echo x | gcloud compute instances delete foo --project dev-env-430408",
    "sudo gcloud compute instances delete foo --project dev-env-430408",
], ids=lambda c: c.split()[0])
def test_real_invocations_still_blocked(command):
    assert is_denied(command, amb=ambient(project="dev-env-430408", kube="dev-gke"))
