from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import html
import json
import os
import shutil
import sys
import time
import zipfile

from .production import load_production_spec, init_production_project, save_production_spec
from .qec_final_export import FinalExportResult, run_production_final_export, read_package_version


@dataclass
class ReleaseValidationIssue:
    key: str
    path: str
    severity: str
    message: str

    def summary(self) -> str:
        return (
            "ReleaseValidationIssue\n"
            f"  key: {self.key}\n"
            f"  severity: {self.severity}\n"
            f"  path: {self.path}\n"
            f"  message: {self.message}"
        )


@dataclass
class ReleaseValidationReport:
    project_name: str
    checked: int
    passed: int
    failed: int
    issues: list[ReleaseValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def summary(self) -> str:
        return (
            "ReleaseValidationReport\n"
            f"  project: {self.project_name}\n"
            f"  checked: {self.checked}\n"
            f"  passed: {self.passed}\n"
            f"  failed: {self.failed}\n"
            f"  ok: {self.ok}"
        )


@dataclass
class ReleasePackageResult:
    project_name: str
    output_dir: str
    final_export: FinalExportResult | None
    validation: ReleaseValidationReport
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ReleasePackageResult\n"
            f"  project: {self.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  validation_ok: {self.validation.ok}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def required_final_artifact_keys() -> list[str]:
    return [
        "latex_manuscript",
        "thesis_appendix",
        "reproducibility_checklist",
        "version_lockfile",
        "final_command_summary",
        "figures_manifest",
        "final_export_report",
        "manifest",
        "final_export_archive",
    ]


def validate_final_export_artifacts(final_export: FinalExportResult) -> ReleaseValidationReport:
    issues: list[ReleaseValidationIssue] = []
    checked = 0
    passed = 0

    for key in required_final_artifact_keys():
        checked += 1
        value = final_export.artifacts.get(key, "")
        if not value:
            issues.append(ReleaseValidationIssue(key, "", "error", "Missing artifact key."))
            continue
        path = Path(value)
        if not path.exists():
            issues.append(ReleaseValidationIssue(key, str(path), "error", "Artifact path does not exist."))
        else:
            passed += 1

    return ReleaseValidationReport(
        project_name=final_export.project_name,
        checked=checked,
        passed=passed,
        failed=len(issues),
        issues=issues,
    )


def export_validation_report(report: ReleaseValidationReport, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AZM-QOS v4.9 Release Validation Report",
        "",
        "```text",
        report.summary(),
        "```",
        "",
    ]
    if report.issues:
        lines.append("## Issues")
        lines.append("")
        for issue in report.issues:
            lines.extend(["```text", issue.summary(), "```", ""])
    else:
        lines.append("No blocking artifact issues were found.")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_clean_command_table(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = r"""
# AZM-QOS v4.9 Clean Command Table

| Purpose | Command |
|---|---|
| Install editable package | `python -m pip install -e .` |
| Initialize production project | `azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project` |
| Create production plan | `azmqos production-plan --config outputs\production_project\azmqos_production.json` |
| Stable integrated workflow | `azmqos stable-run --config outputs\production_project\azmqos_production.json --backend fallback --max-components 2 --shots 64` |
| Hardware analysis | `azmqos production-hardware-analysis --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3` |
| Final export | `azmqos production-final-export --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3` |
| All-in-one release | `azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3` |
"""
    output_path.write_text(text.strip() + "\n", encoding="utf-8")
    return output_path


def make_windows_troubleshooting_guide(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = r"""
# Windows / PowerShell Troubleshooting

## 1. Missing `azmqos_production.json`

Run:

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

Then:

```powershell
azmqos production-plan --config outputs\production_project\azmqos_production.json
```

## 2. New version installed but old commands appear

From inside the new package folder, run:

```powershell
python -m pip install -e .
```

Then close and reopen PowerShell.

## 3. Path confusion

Prefer relative paths from inside the package folder:

```powershell
outputs\production_project\azmqos_production.json
```

Avoid mixing old extracted ZIP folders and new extracted ZIP folders.

## 4. Recommended clean sequence

```powershell
cd path\to\AZM_QOS_v4_9
python -m pip install -e .
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```
"""
    output_path.write_text(text.strip() + "\n", encoding="utf-8")
    return output_path


def make_html_final_report(result: ReleasePackageResult, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_rows = "\n".join(
        f"<tr><td>{html.escape(k)}</td><td><code>{html.escape(str(v))}</code></td></tr>"
        for k, v in result.artifacts.items()
    )
    issue_rows = "\n".join(
        f"<tr><td>{html.escape(i.key)}</td><td>{html.escape(i.severity)}</td><td><code>{html.escape(i.path)}</code></td><td>{html.escape(i.message)}</td></tr>"
        for i in result.validation.issues
    ) or "<tr><td colspan='4'>No validation issues.</td></tr>"
    body = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AZM-QOS v4.9 Release Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.45; }}
code {{ background: #f4f4f4; padding: 0.1rem 0.25rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
td, th {{ border: 1px solid #ccc; padding: 0.45rem; vertical-align: top; }}
th {{ background: #eee; }}
.ok {{ color: #147a1d; font-weight: bold; }}
.warn {{ color: #a45b00; font-weight: bold; }}
</style>
</head>
<body>
<h1>AZM-QOS v4.9 Release Report</h1>
<pre>{html.escape(result.summary())}</pre>
<h2>Validation</h2>
<p class="{ 'ok' if result.validation.ok else 'warn' }">Validation OK: {result.validation.ok}</p>
<pre>{html.escape(result.validation.summary())}</pre>
<table>
<tr><th>Key</th><th>Severity</th><th>Path</th><th>Message</th></tr>
{issue_rows}
</table>
<h2>Artifacts</h2>
<table>
<tr><th>Artifact</th><th>Path</th></tr>
{artifact_rows}
</table>
<h2>Warnings</h2>
<ul>
{''.join(f'<li>{html.escape(w)}</li>' for w in result.warnings) or '<li>None</li>'}
</ul>
</body>
</html>
"""
    output_path.write_text(body, encoding="utf-8")
    return output_path


def should_exclude_from_minimal(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    excluded_dirs = {"outputs", "__pycache__", ".git", ".pytest_cache", ".mypy_cache", "dist", "build", "*.egg-info"}
    if any(part in excluded_dirs for part in rel_parts):
        return True
    if any(part.endswith(".egg-info") for part in rel_parts):
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    return False


def create_minimal_release_package(package_root, output_dir, archive_name: str = "AZM_QOS_v4_9_minimal_clean_package.zip"):
    package_root = Path(package_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / archive_name
    if archive_path.exists():
        archive_path.unlink()

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in package_root.rglob("*"):
            if path.is_file() and not should_exclude_from_minimal(path, package_root):
                z.write(path, arcname=Path(package_root.name) / path.relative_to(package_root))
    return archive_path


def make_release_manifest(result: ReleasePackageResult, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "package": "AZM-QOS v4.9 release polish",
        "summary": result.summary(),
        "validation": asdict(result.validation),
        "warnings": result.warnings,
        "artifacts": result.artifacts,
        "metadata": result.metadata,
    }
    output_path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    return output_path


def run_release_packaging_from_final_export(
    final_export: FinalExportResult,
    output_dir,
    package_root: str | Path | None = None,
) -> ReleasePackageResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_root = Path(package_root) if package_root else Path(__file__).resolve().parents[1]

    validation = validate_final_export_artifacts(final_export)
    artifacts = dict(final_export.artifacts)

    artifacts["release_validation_report"] = str(export_validation_report(validation, output_dir / "release_validation_report.md"))
    artifacts["clean_command_table"] = str(make_clean_command_table(output_dir / "clean_command_table.md"))
    artifacts["windows_troubleshooting"] = str(make_windows_troubleshooting_guide(output_dir / "windows_troubleshooting.md"))
    artifacts["minimal_clean_package"] = str(create_minimal_release_package(package_root, output_dir / "minimal_package"))

    result = ReleasePackageResult(
        project_name=final_export.project_name,
        output_dir=str(output_dir),
        final_export=final_export,
        validation=validation,
        artifacts=artifacts,
        warnings=list(final_export.warnings),
        metadata={
            "package_version": read_package_version(package_root),
            "created_at_unix": time.time(),
        },
    )
    artifacts["html_final_report"] = str(make_html_final_report(result, output_dir / "release_report.html"))
    artifacts["release_manifest"] = str(make_release_manifest(result, output_dir / "release_manifest.json"))

    return ReleasePackageResult(
        project_name=final_export.project_name,
        output_dir=str(output_dir),
        final_export=final_export,
        validation=validation,
        artifacts=artifacts,
        warnings=list(final_export.warnings),
        metadata={
            "package_version": read_package_version(package_root),
            "created_at_unix": time.time(),
        },
    )


def run_production_release(
    spec_or_path,
    backend_name: str = "ibm_fez",
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    job_ids_file: str | None = None,
    enable_runtime_fetch: bool = False,
    force_refresh: bool = False,
    calibration_file: str | None = None,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    final_export = run_production_final_export(
        spec,
        backend_name=backend_name,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        job_ids_file=job_ids_file,
        enable_runtime_fetch=enable_runtime_fetch,
        force_refresh=force_refresh,
        calibration_file=calibration_file,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )
    output_dir = Path(spec.output_dir) / "release_v4_9"
    return run_release_packaging_from_final_export(final_export, output_dir)


def run_release_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    spec, artifacts = init_production_project(output_dir / "production_project", project_name="release_demo_project")
    spec = load_production_spec(artifacts["config_path"])
    template_registry = Path(__file__).resolve().parents[1] / "templates" / "endvqs_real_terms_template.json"
    if template_registry.exists():
        spec.component_registry_path = str(template_registry)
        save_production_spec(spec, artifacts["config_path"])

    return run_production_release(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=1,
        shots=32,
        rounds=1,
    )


def run_minimal_package_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_root = Path(__file__).resolve().parents[1]
    archive = create_minimal_release_package(package_root, output_dir)
    manifest = {
        "package": "AZM-QOS v4.9 minimal package demo",
        "archive": str(archive),
        "exists": archive.exists(),
    }
    manifest_path = output_dir / "minimal_package_demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return archive, manifest_path
