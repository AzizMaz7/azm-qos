from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import shutil
import time
import zipfile

from .project_config import (
    AZMQOSProjectConfig,
    init_project,
    load_project_config,
    save_project_config,
    validate_project_config,
)
from .plugin_registry import (
    default_plugin_registry,
    save_plugin_registry,
    make_plugin_registry_report,
)
from .experiment_db import (
    create_demo_run_database,
    ExperimentDatabase,
    export_run_table_csv,
    export_dashboard_json,
    make_run_database_report,
)
from .dashboard import build_dashboard_package
from .job_sync import run_mock_sync_workflow
from .calibration_mitigation import run_mock_mitigation_workflow
from .uncertainty import run_mock_uncertainty_workflow


@dataclass
class IntegratedWorkflowResult:
    config: AZMQOSProjectConfig
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    steps: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "IntegratedWorkflowResult\n"
            f"  project: {self.config.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  steps: {self.steps}\n"
            f"  warnings: {self.warnings}"
        )


def _copy_or_note(src, dst):
    src = Path(src)
    dst = Path(dst)
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return str(dst)
    return str(src)


def make_manuscript_scaffold(config: AZMQOSProjectConfig, artifacts: dict[str, str], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "manuscript_scaffold.md"
    tex_path = output_dir / "manuscript_scaffold.tex"

    md_lines = [
        f"# {config.project_name}: AZM-QOS Integrated Research Report",
        "",
        "## Abstract",
        "",
        "This scaffold summarizes an AZM-QOS integrated workflow combining END/VQS workloads, hardware-result management, mitigation, uncertainty analysis, synchronization, and dashboard generation.",
        "",
        "## Workflow artifacts",
        "",
    ]
    for key, value in artifacts.items():
        md_lines.append(f"- **{key}**: `{value}`")
    md_lines.extend([
        "",
        "## Notes",
        "",
        "Replace this scaffold with project-specific scientific interpretation, equations, figures, and references.",
        "",
    ])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{hyperref}}
\\title{{{config.project_name}: AZM-QOS Integrated Research Report}}
\\author{{AZM-QOS v3.0}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\begin{{abstract}}
This scaffold summarizes an AZM-QOS integrated workflow combining END/VQS workloads, hardware-result management, mitigation, uncertainty analysis, synchronization, and dashboard generation.
\\end{{abstract}}

\\section{{Workflow}}
The project configuration was executed in mode: \\texttt{{{config.workflow.mode}}}.

\\section{{Artifacts}}
See the generated project summary report and reproducibility archive for all artifacts.

\\section{{Notes}}
Replace this scaffold with project-specific scientific interpretation, equations, figures, and references.

\\end{{document}}
"""
    tex_path.write_text(tex.strip() + "\n", encoding="utf-8")

    return {"manuscript_markdown": str(md_path), "manuscript_latex": str(tex_path)}


def make_project_summary_report(result: IntegratedWorkflowResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.0 Integrated Project Summary",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Configuration",
        "",
        "```text",
        result.config.summary(),
        "```",
        "",
        "## Steps",
        "",
    ]
    for key, value in result.steps.items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(["", "## Artifacts", ""])
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
    lines.extend([
        "",
        "## Safety note",
        "",
        "The v3.0 integrated app uses mock/local/dry-run-safe workflows by default and does not submit real IBM hardware jobs.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def create_final_archive(output_dir, archive_path):
    output_dir = Path(output_dir)
    archive_path = Path(archive_path)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in output_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                z.write(path, arcname=path.relative_to(output_dir))
    return archive_path


def run_integrated_workflow(config_or_path) -> IntegratedWorkflowResult:
    if isinstance(config_or_path, (str, Path)):
        config = load_project_config(config_or_path)
    else:
        config = config_or_path

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = validate_project_config(config)
    artifacts = {}
    steps = {}

    # Always save resolved config.
    artifacts["project_config"] = str(save_project_config(config, output_dir / "azmqos_project_resolved.json"))
    steps["config"] = "saved"

    # Plugin registry.
    registry = default_plugin_registry()
    artifacts["plugin_registry_json"] = str(save_plugin_registry(registry, output_dir / "registry" / "plugin_registry.json"))
    artifacts["plugin_registry_report"] = str(make_plugin_registry_report(registry, output_dir / "reports" / "plugin_registry_report.md"))
    steps["plugin_registry"] = "created"

    # Demo database / local records.
    db, records, db_artifacts = create_demo_run_database(output_dir / "database")
    artifacts.update({f"database_{k}": v for k, v in db_artifacts.items()})
    artifacts["database_jsonl"] = str(db.path)
    steps["database"] = f"created {len(records)} demo records"

    # Sync workflow.
    if config.workflow.run_sync:
        sync_summary = run_mock_sync_workflow(output_dir / "sync")
        artifacts["sync_manifest"] = str(output_dir / "sync" / "sync_manifest.json")
        artifacts["sync_report"] = str(output_dir / "sync" / "sync_report.md")
        steps["sync"] = sync_summary.summary()
    else:
        steps["sync"] = "skipped"

    # Mitigation workflow.
    if config.workflow.run_mitigation:
        mitigation = run_mock_mitigation_workflow(output_dir / "mitigation")
        artifacts["mitigation_manifest"] = mitigation.artifacts.get("manifest", "")
        artifacts["mitigation_report"] = mitigation.artifacts.get("markdown_report", "")
        steps["mitigation"] = "completed"
    else:
        steps["mitigation"] = "skipped"

    # Uncertainty workflow.
    if config.workflow.run_uncertainty:
        uncertainty = run_mock_uncertainty_workflow(output_dir / "uncertainty", n_bootstrap=200)
        artifacts["uncertainty_manifest"] = uncertainty.artifacts.get("manifest", "")
        artifacts["uncertainty_report"] = uncertainty.artifacts.get("markdown_report", "")
        steps["uncertainty"] = "completed"
    else:
        steps["uncertainty"] = "skipped"

    # Dashboard.
    if config.workflow.build_dashboard:
        dashboard = build_dashboard_package(output_dir / "dashboard")
        artifacts["dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
        artifacts["dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")
        artifacts["artifact_browser_html"] = dashboard.artifacts.get("artifact_browser_html", "")
        steps["dashboard"] = dashboard.summary_text()
    else:
        steps["dashboard"] = "skipped"

    # Manuscript scaffold.
    if config.workflow.export_manuscript:
        manuscript = make_manuscript_scaffold(config, artifacts, output_dir / "reports" / "manuscript")
        artifacts.update(manuscript)
        steps["manuscript"] = "created"
    else:
        steps["manuscript"] = "skipped"

    result = IntegratedWorkflowResult(
        config=config,
        output_dir=str(output_dir),
        artifacts=artifacts,
        steps=steps,
        warnings=warnings,
        metadata={"completed_at_unix": time.time()},
    )

    artifacts["project_summary_report"] = str(make_project_summary_report(result, output_dir / "reports" / "project_summary.md"))

    # Save machine-readable manifest after report.
    manifest_path = output_dir / "azmqos_integrated_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.0 integrated workflow",
        "config": config.to_dict(),
        "steps": steps,
        "warnings": warnings,
        "artifacts": artifacts,
        "metadata": result.metadata,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["integrated_manifest"] = str(manifest_path)

    if config.workflow.create_final_archive:
        archive_path = create_final_archive(output_dir, output_dir / "archives" / f"{config.project_name}_azmqos_archive.zip")
        artifacts["final_archive"] = str(archive_path)
        steps["archive"] = "created"
    else:
        steps["archive"] = "skipped"

    return IntegratedWorkflowResult(
        config=config,
        output_dir=str(output_dir),
        artifacts=artifacts,
        steps=steps,
        warnings=warnings,
        metadata={"completed_at_unix": time.time()},
    )
