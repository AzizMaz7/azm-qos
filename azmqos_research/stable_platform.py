from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import shutil
import time
import zipfile

from .production import (
    ProductionProjectSpec,
    load_production_spec,
    init_production_project,
    make_production_plan,
    export_production_plan_json,
    export_production_plan_csv,
    make_production_plan_report,
)
from .production_pauli_execution import run_production_pauli_execution
from .qiskit_pauli_execution import run_production_qiskit_execution
from .endvqs_stateprep import run_production_endvqs_execution
from .derivative_estimators import run_production_derivative_estimators
from .derivative_mitigation import run_production_mitigated_derivatives
from .dashboard import build_dashboard_package


@dataclass
class StableWorkflowResult:
    project_name: str
    output_dir: str
    steps: dict[str, str] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "StableWorkflowResult\n"
            f"  project_name: {self.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  steps: {len(self.steps)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def ensure_production_config(output_dir, project_name="my_endvqs_project"):
    """Create azmqos_production.json if it does not exist."""
    output_dir = Path(output_dir)
    config_path = output_dir / "azmqos_production.json"
    if config_path.exists():
        return str(config_path), False

    spec, artifacts = init_production_project(output_dir, project_name=project_name)
    return artifacts["config_path"], True


def make_stable_manuscript_scaffold(result: StableWorkflowResult, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {result.project_name}: AZM-QOS v4.0 Stable END/VQS Workflow",
        "",
        "## Abstract",
        "",
        "This manuscript scaffold summarizes a stable AZM-QOS END/VQS workflow including Pauli compilation, grouped Pauli execution, Qiskit/fallback execution, END/VQS state-preparation hooks, derivative estimation, derivative mitigation, dashboards, and reproducibility archives.",
        "",
        "## Workflow steps",
        "",
    ]
    for key, value in result.steps.items():
        lines.append(f"- **{key}**: {value}")

    lines.extend(["", "## Artifacts", ""])
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend([
        "",
        "## Scientific note",
        "",
        "The v4.0 platform is stable for workflow testing and reproducibility. Scaffold ansatz and mitigation models should be replaced by final derived END/VQS circuits and device-specific calibrations before publication-quality hardware conclusions.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_stable_report(result: StableWorkflowResult, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AZM-QOS v4.0 Stable Integrated Platform Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Steps",
        "",
    ]
    for key, value in result.steps.items():
        lines.append(f"- **{key}**: {value}")
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
    lines.extend(["", "## Artifacts", ""])
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Required first command",
        "",
        "```powershell",
        r"azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project",
        "```",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def create_stable_archive(output_dir, archive_path):
    output_dir = Path(output_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in output_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                z.write(path, arcname=path.relative_to(output_dir))
    return archive_path


def run_stable_workflow(
    config_path,
    backend: str = "fallback",
    max_components: int | None = 2,
    shots: int | None = 64,
):
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Production config not found: {config_path}\n\n"
            "Run this first:\n"
            r"azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project"
        )

    spec = load_production_spec(config_path)
    output_dir = Path(spec.output_dir)
    stable_dir = output_dir / "stable_v4_0"
    stable_dir.mkdir(parents=True, exist_ok=True)

    steps = {}
    artifacts = {}
    warnings = []

    # Step 1: plan.
    plan = make_production_plan(spec)
    plan_dir = stable_dir / "plan"
    artifacts["production_plan_json"] = str(export_production_plan_json(plan, plan_dir / "production_plan.json"))
    artifacts["production_plan_csv"] = str(export_production_plan_csv(plan, plan_dir / "production_plan.csv"))
    artifacts["production_plan_report"] = str(make_production_plan_report(plan, plan_dir / "production_plan_report.md"))
    steps["production_plan"] = f"created {len(plan.items)} plan items"
    warnings.extend(plan.warnings)

    # Step 2: grouped Pauli execution.
    pauli = run_production_pauli_execution(config_path, max_components=max_components, shots_per_group=shots)
    artifacts["pauli_manifest"] = pauli.artifacts.get("production_pauli_execution_manifest", "")
    artifacts["pauli_M_estimates"] = pauli.artifacts.get("M_estimates_csv", "")
    artifacts["pauli_V_estimates"] = pauli.artifacts.get("V_estimates_csv", "")
    steps["pauli_execution"] = f"estimated {len(pauli.component_estimates)} components"

    # Step 3: Qiskit/fallback Pauli execution.
    qiskit = run_production_qiskit_execution(
        config_path,
        backend=backend,
        max_components=max_components,
        shots=shots,
    )
    artifacts["qiskit_manifest"] = qiskit.artifacts.get("production_qiskit_execution_manifest", "")
    artifacts["qiskit_M_estimates"] = qiskit.artifacts.get("M_estimates_csv", "")
    artifacts["qiskit_V_estimates"] = qiskit.artifacts.get("V_estimates_csv", "")
    steps["qiskit_execution"] = f"estimated {len(qiskit.component_estimates)} components with backend={backend}"

    # Step 4: END/VQS state-prep execution.
    endvqs = run_production_endvqs_execution(
        config_path,
        backend=backend,
        max_components=max_components,
        shots=shots,
    )
    artifacts["endvqs_manifest"] = endvqs["artifacts"].get("manifest", "")
    artifacts["endvqs_results_csv"] = endvqs["artifacts"].get("endvqs_execution_results_csv", "")
    steps["endvqs_stateprep_execution"] = f"executed {len(endvqs['results'])} components"

    # Step 5: derivatives.
    derivatives = run_production_derivative_estimators(
        config_path,
        backend=backend,
        max_components=max_components,
        shots=shots,
    )
    artifacts["derivatives_manifest"] = derivatives.artifacts.get("manifest", "")
    artifacts["M_derivatives_csv"] = derivatives.artifacts.get("M_derivatives_csv", "")
    artifacts["V_derivatives_csv"] = derivatives.artifacts.get("V_derivatives_csv", "")
    steps["derivative_estimators"] = f"computed {len(derivatives.component_derivatives)} derivative estimates"

    # Step 6: mitigated derivatives.
    mitigated = run_production_mitigated_derivatives(
        config_path,
        backend=backend,
        max_components=max_components,
        shots=shots,
    )
    artifacts["mitigated_derivatives_manifest"] = mitigated.artifacts.get("manifest", "")
    artifacts["M_mitigated_derivatives_csv"] = mitigated.artifacts.get("M_mitigated_derivatives_csv", "")
    artifacts["V_mitigated_derivatives_csv"] = mitigated.artifacts.get("V_mitigated_derivatives_csv", "")
    steps["derivative_mitigation"] = f"computed {len(mitigated.mitigated_derivatives)} mitigated derivative estimates"

    # Step 7: dashboard.
    # Prefer Pauli execution database for stable dashboard.
    pauli_db = output_dir / "database" / "production_pauli_execution_runs.jsonl"
    if pauli_db.exists():
        dashboard = build_dashboard_package(stable_dir / "dashboard", database_path=pauli_db)
        artifacts["stable_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
        artifacts["stable_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")
        steps["dashboard"] = "created stable dashboard"
    else:
        warnings.append("Pauli execution database not found; skipped stable dashboard.")
        steps["dashboard"] = "skipped"

    result = StableWorkflowResult(
        project_name=spec.project_name,
        output_dir=str(output_dir),
        steps=steps,
        artifacts=artifacts,
        warnings=warnings,
        metadata={
            "backend": backend,
            "max_components": max_components,
            "shots": shots,
            "completed_at_unix": time.time(),
        },
    )

    # Step 8: reports and archive.
    artifacts["stable_report"] = str(make_stable_report(result, stable_dir / "stable_platform_report.md"))
    artifacts["manuscript_scaffold"] = str(make_stable_manuscript_scaffold(result, stable_dir / "stable_manuscript_scaffold.md"))

    manifest_path = stable_dir / "stable_workflow_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.0 stable integrated platform",
        "summary": result.summary(),
        "steps": steps,
        "warnings": warnings,
        "artifacts": artifacts,
        "metadata": result.metadata,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["stable_manifest"] = str(manifest_path)

    archive_path = create_stable_archive(output_dir, output_dir / "archives" / f"{spec.project_name}_v4_0_stable_archive.zip")
    artifacts["stable_archive"] = str(archive_path)
    steps["archive"] = "created stable reproducibility archive"

    return StableWorkflowResult(
        project_name=spec.project_name,
        output_dir=str(output_dir),
        steps=steps,
        artifacts=artifacts,
        warnings=warnings,
        metadata={
            "backend": backend,
            "max_components": max_components,
            "shots": shots,
            "completed_at_unix": time.time(),
        },
    )


def run_stable_smoke_test(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path, created = ensure_production_config(output_dir / "production_project", project_name="stable_smoke_test_project")
    spec = load_production_spec(config_path)

    # Use bundled template registry if the default relative path is available.
    # The caller's package root is two levels above this file.
    package_root = Path(__file__).resolve().parents[1]
    template_registry = package_root / "templates" / "endvqs_real_terms_template.json"
    if template_registry.exists():
        spec.component_registry_path = str(template_registry)
        from .production import save_production_spec
        save_production_spec(spec, config_path)

    result = run_stable_workflow(config_path, backend="fallback", max_components=1, shots=32)
    result.metadata["config_created"] = created
    return result
