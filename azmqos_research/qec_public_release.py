from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import inspect
import json
import textwrap
import time

PUBLIC_VERSION = "5.0.0"
PUBLIC_RELEASE_NAME = "AZM-QOS Stable Public Research Release"


@dataclass
class PublicReleaseManifest:
    package_name: str = "AZM-QOS"
    version: str = PUBLIC_VERSION
    release_name: str = PUBLIC_RELEASE_NAME
    semantic_versioning: str = "MAJOR.MINOR.PATCH"
    stability: str = "stable-public-research"
    created_at_unix: float = field(default_factory=time.time)
    highlights: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "PublicReleaseManifest\n"
            f"  package_name: {self.package_name}\n"
            f"  version: {self.version}\n"
            f"  release_name: {self.release_name}\n"
            f"  stability: {self.stability}\n"
            f"  highlights: {len(self.highlights)}\n"
            f"  entry_points: {len(self.entry_points)}"
        )


@dataclass
class APIReferenceEntry:
    module: str
    name: str
    kind: str
    signature: str
    summary: str = ""

    def summary_text(self) -> str:
        return f"{self.module}.{self.name} ({self.kind}) {self.signature}"


@dataclass
class PublicReleaseValidation:
    version: str
    checks: dict[str, bool]
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(self.checks.values())

    def summary(self) -> str:
        passed = sum(1 for v in self.checks.values() if v)
        return (
            "PublicReleaseValidation\n"
            f"  version: {self.version}\n"
            f"  passed: {passed}/{len(self.checks)}\n"
            f"  ok: {self.ok}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def make_public_release_manifest() -> PublicReleaseManifest:
    return PublicReleaseManifest(
        highlights=[
            "Stable END/VQS workflow scaffolds",
            "QEC logical mapping and syndrome decoding layers",
            "Fault-tolerant QEC circuit and hardware dry-run scaffolds",
            "Runtime synchronization and hardware-analysis reports",
            "Final manuscript/thesis export",
            "Release-polish and one-command workflow utilities",
            "Public API/reference documentation scaffolds",
        ],
        entry_points=[
            "azmqos production-init",
            "azmqos stable-run",
            "azmqos production-qec-estimate",
            "azmqos production-qec-decode",
            "azmqos production-ft-qec",
            "azmqos production-qec-hardware-dry-run",
            "azmqos production-qec-hardware-sync",
            "azmqos production-runtime-sync",
            "azmqos production-hardware-analysis",
            "azmqos production-final-export",
            "azmqos production-release-run",
            "azmqos public-release-info",
            "azmqos public-release-validate",
        ],
        metadata={
            "scientific_status": "research software with scaffolded and optional hardware workflows",
            "hardware_note": "No command submits hardware jobs unless explicitly extended by the user.",
        },
    )


def export_public_release_manifest(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = make_public_release_manifest()
    path.write_text(json.dumps(asdict(manifest), indent=2, default=_json_default), encoding="utf-8")
    return path


def build_api_reference_entries() -> list[APIReferenceEntry]:
    module_names = [
        "azmqos_research.qec_logical",
        "azmqos_research.qec_decoder",
        "azmqos_research.qec_fault_tolerant",
        "azmqos_research.qec_hardware",
        "azmqos_research.qec_hardware_sync",
        "azmqos_research.qec_runtime_fetch",
        "azmqos_research.qec_hardware_analysis",
        "azmqos_research.qec_final_export",
        "azmqos_research.qec_release",
        "azmqos_research.qec_public_release",
    ]
    entries: list[APIReferenceEntry] = []
    for module_name in module_names:
        try:
            module = __import__(module_name, fromlist=["*"])
        except Exception as exc:
            entries.append(APIReferenceEntry(module_name, "__import_error__", "error", "", str(exc)))
            continue
        for name, obj in sorted(vars(module).items()):
            if name.startswith("_"):
                continue
            if inspect.isclass(obj):
                entries.append(APIReferenceEntry(module_name, name, "class", ""))
            elif inspect.isfunction(obj):
                try:
                    sig = str(inspect.signature(obj))
                except Exception:
                    sig = "(...)"
                first = (inspect.getdoc(obj) or "").splitlines()[0] if inspect.getdoc(obj) else ""
                entries.append(APIReferenceEntry(module_name, name, "function", sig, first))
    return entries


def export_api_reference_markdown(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = build_api_reference_entries()
    lines = ["# AZM-QOS v5.0 Public API Reference", ""]
    current_module = None
    for entry in entries:
        if entry.module != current_module:
            current_module = entry.module
            lines.extend(["", f"## `{current_module}`", ""])
        if entry.kind == "function":
            lines.append(f"- **function** `{entry.name}{entry.signature}`")
        elif entry.kind == "class":
            lines.append(f"- **class** `{entry.name}`")
        else:
            lines.append(f"- **{entry.kind}** `{entry.name}` — {entry.summary}")
        if entry.summary and entry.kind != "error":
            lines.append(f"  - {entry.summary}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_paper_reproduction_index(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = r"""
# Paper Reproduction Index

## Minimal local smoke workflow

```powershell
python -m pip install -e .
azmqos public-release-info --output-dir outputs\public_release_info
azmqos public-release-validate --output-dir outputs\public_release_validate
```

## Full production scaffold workflow

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
azmqos production-release-run --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Hardware-data workflow

1. Run hardware dry-run.
2. Export real job IDs/counts.
3. Run Runtime sync with imported job IDs.
4. Run hardware analysis with calibration metadata.
5. Run final export.

Synthetic fallback results are software-validation results, not hardware claims.
"""
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return path


def export_docs_site_scaffold(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.md").write_text(
        "# AZM-QOS v5.0 Documentation Site\n\n"
        "## Pages\n\n"
        "- [Quick Start](quick_start.md)\n"
        "- [API Reference](api_reference.md)\n"
        "- [Paper Reproduction](paper_reproduction.md)\n"
        "- [Troubleshooting](troubleshooting.md)\n",
        encoding="utf-8",
    )
    (output_dir / "quick_start.md").write_text(
        "# Quick Start\n\n"
        "```powershell\n"
        "python -m pip install -e .\n"
        "azmqos production-init --output-dir outputs\\production_project --project-name my_endvqs_project\n"
        "azmqos production-release-run --config outputs\\production_project\\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3\n"
        "```\n",
        encoding="utf-8",
    )
    (output_dir / "troubleshooting.md").write_text(
        "# Troubleshooting\n\n"
        "Run `azmqos production-init --output-dir outputs\\production_project --project-name my_endvqs_project` "
        "first if the production config is missing.\n",
        encoding="utf-8",
    )
    export_api_reference_markdown(output_dir / "api_reference.md")
    export_paper_reproduction_index(output_dir / "paper_reproduction.md")
    return output_dir


def export_scaffold_label_cleanup_report(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = """
# Scaffold Label Cleanup Report

AZM-QOS v5.0 keeps scaffold labels where the implementation is intentionally a research scaffold.
This makes synthetic, deterministic, or placeholder components explicit.

## Labels retained

- `synthetic`: deterministic local fallback data
- `scaffold`: research workflow scaffold not yet a final hardware claim
- `dry_run`: manifest or local transpilation result; no hardware job submitted
- `runtime`: real Runtime fetch path, only when explicitly enabled and available

## Publication guidance

Replace or supplement scaffold-labeled artifacts with real hardware data, calibration metadata,
and validated decoders before making device-performance claims.
"""
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return path


def export_citation_metadata(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "cff-version": "1.2.0",
        "title": "AZM-QOS",
        "version": PUBLIC_VERSION,
        "message": "If you use this research software, cite the associated manuscript or repository.",
        "type": "software",
        "authors": [{"name": "AZM-QOS contributors"}],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def validate_public_release(package_root=None) -> PublicReleaseValidation:
    package_root = Path(package_root) if package_root else Path(__file__).resolve().parents[1]
    checks = {
        "readme_exists": (package_root / "README.md").exists(),
        "pyproject_exists": (package_root / "pyproject.toml").exists(),
        "public_module_exists": (package_root / "azmqos_research" / "qec_public_release.py").exists(),
        "release_module_exists": (package_root / "azmqos_research" / "qec_release.py").exists(),
        "final_export_module_exists": (package_root / "azmqos_research" / "qec_final_export.py").exists(),
        "tests_exist": (package_root / "tests" / "test_v5_0_public_release.py").exists(),
        "examples_exist": (package_root / "examples" / "public_release_info_demo.py").exists(),
        "docs_exist": (package_root / "docs" / "V5_0_STABLE_PUBLIC_RELEASE.md").exists(),
    }
    warnings = []
    readme = package_root / "README.md"
    if readme.exists() and "production-init" not in readme.read_text(encoding="utf-8"):
        checks["readme_mentions_production_init"] = False
        warnings.append("README does not mention production-init.")
    else:
        checks["readme_mentions_production_init"] = True
    return PublicReleaseValidation(PUBLIC_VERSION, checks, warnings)


def export_public_validation_report(path, package_root=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = validate_public_release(package_root)
    lines = ["# AZM-QOS v5.0 Public Release Validation", "", "```text", validation.summary(), "```", ""]
    for key, value in validation.checks.items():
        mark = "✅" if value else "❌"
        lines.append(f"- {mark} **{key}**")
    if validation.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in validation.warnings:
            lines.append(f"- {warning}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_public_release_info(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "public_release_manifest": str(export_public_release_manifest(output_dir / "public_release_manifest.json")),
        "api_reference": str(export_api_reference_markdown(output_dir / "api_reference.md")),
        "docs_site": str(export_docs_site_scaffold(output_dir / "docs_site")),
        "paper_reproduction_index": str(export_paper_reproduction_index(output_dir / "paper_reproduction_index.md")),
        "scaffold_label_cleanup_report": str(export_scaffold_label_cleanup_report(output_dir / "scaffold_label_cleanup_report.md")),
        "citation_metadata": str(export_citation_metadata(output_dir / "CITATION.cff.json")),
    }
    summary_path = output_dir / "public_release_summary.md"
    manifest = make_public_release_manifest()
    summary_path.write_text(
        "# AZM-QOS v5.0 Public Release Summary\n\n"
        "```text\n"
        f"{manifest.summary()}\n"
        "```\n\n"
        "## Artifacts\n\n"
        + "\n".join(f"- **{k}**: `{v}`" for k, v in artifacts.items())
        + "\n",
        encoding="utf-8",
    )
    artifacts["public_release_summary"] = str(summary_path)
    return artifacts


def run_public_release_validate(output_dir, package_root=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = export_public_validation_report(output_dir / "public_release_validation.md", package_root=package_root)
    validation = validate_public_release(package_root)
    manifest = output_dir / "public_release_validation.json"
    manifest.write_text(json.dumps(asdict(validation), indent=2, default=_json_default), encoding="utf-8")
    return {"validation_report": str(report), "validation_json": str(manifest), "ok": validation.ok}
