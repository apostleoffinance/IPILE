from pathlib import Path




REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "cloudflare-preview-deploy.yml"
)


def test_production_frontend_deployment_is_manual_only_and_uses_main() -> None:
    workflow = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")
    trigger_section = workflow.split("jobs:", maxsplit=1)[0]

    assert "workflow_dispatch:" in trigger_section
    assert "push:" not in trigger_section
    assert "pull_request:" not in trigger_section
    assert "ref: main" in workflow
    assert "environment: production" in workflow


def test_production_frontend_deployment_requires_explicit_dispatch_approval() -> None:
    workflow = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")

    assert "release_approval:" in workflow
    assert "APPROVE_PRODUCTION_FRONTEND_DEPLOYMENT" in workflow
    assert "Require explicit production deployment approval" in workflow


def test_production_frontend_deployment_checks_backend_health_before_cutover() -> None:
    workflow = PRODUCTION_WORKFLOW.read_text(encoding="utf-8")
    health_check = workflow.split(
        "Verify production backend health before frontend deployment", maxsplit=1
    )[1]
    deployment = health_check.split("Bind production API and deploy once", maxsplit=1)[0]

    assert "/health/live" in deployment
    assert "/health" in deployment
    assert "curl --fail" in deployment
