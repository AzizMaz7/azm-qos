from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import time
import uuid
import zipfile

from .experiment_db import (
    ExperimentDatabase,
    BackendMetadataRecord,
    new_run_record,
    artifact_from_path,
    export_run_table_csv,
    export_dashboard_json,
    make_run_database_report,
)
from .dashboard import build_dashboard_package


@dataclass
class ObservableSelection:
    families: list[str] = field(default_factory=lambda: ["Mbb", "Mab", "Maa", "Va", "Vb"])
    include_quantities: list[str] = field(default_factory=lambda: ["M", "V"])
    exclude_component_names: list[str] = field(default_factory=list)
    max_components: int | None = None

    def summary(self) -> str:
        return (
            "ObservableSelection\n"
            f"  families: {self.families}\n"
            f"  include_quantities: {self.include_quantities}\n"
            f"  exclude_component_names: {self.exclude_component_names}\n"
            f"  max_components: {self.max_components}"
        )


@dataclass
class ExecutionPolicy:
    mode: str = "simulator"  # simulator, hardware_dry_run, hardware_submit_disabled
    backend_name: str | None = None
    shots: int = 1024
    repeats: int = 10
    allow_hardware_submit: bool = False
    optimization_level: int = 1

    def summary(self) -> str:
        return (
            "ExecutionPolicy\n"
            f"  mode: {self.mode}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  shots: {self.shots}\n"
            f"  repeats: {self.repeats}\n"
            f"  allow_hardware_submit: {self.allow_hardware_submit}\n"
            f"  optimization_level: {self.optimization_level}"
        )


@dataclass
class QueuePolicy:
    max_jobs_per_batch: int = 3
    poll_interval_seconds: int = 60
    auto_resume: bool = True
    fail_fast: bool = False

    def summary(self) -> str:
        return (
            "QueuePolicy\n"
            f"  max_jobs_per_batch: {self.max_jobs_per_batch}\n"
            f"  poll_interval_seconds: {self.poll_interval_seconds}\n"
            f"  auto_resume: {self.auto_resume}\n"
            f"  fail_fast: {self.fail_fast}"
        )


@dataclass
class ManuscriptSettings:
    title: str = "END/VQS Quantum Algorithm Production Results"
    author: str = "AZM-QOS"
    include_bibtex: bool = True
    include_figures: bool = True


@dataclass
class ProductionProjectSpec:
    project_name: str
    azmqos_version: str = "3.1.0"
    description: str = "END/VQS production-run configuration."
    output_dir: str = "outputs/endvqs_production_project"
    component_registry_path: str | None = "templates/endvqs_real_terms_template.json"
    term_registry_path: str | None = None
    observable_selection: ObservableSelection = field(default_factory=ObservableSelection)
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    queue_policy: QueuePolicy = field(default_factory=QueuePolicy)
    manuscript: ManuscriptSettings = field(default_factory=ManuscriptSettings)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ProductionProjectSpec\n"
            f"  project_name: {self.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  component_registry_path: {self.component_registry_path}\n"
            f"  term_registry_path: {self.term_registry_path}\n"
            f"  execution_mode: {self.execution_policy.mode}\n"
            f"  allow_hardware_submit: {self.execution_policy.allow_hardware_submit}"
        )

    def to_dict(self):
        return asdict(self)


@dataclass
class ProductionPlanItem:
    plan_id: str
    component_name: str
    quantity: str
    indices: list[int]
    family: str | None
    n_terms: int
    execution_mode: str
    backend_name: str | None
    shots: int
    status: str = "planned"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"ProductionPlanItem(component={self.component_name}, quantity={self.quantity}, "
            f"indices={self.indices}, family={self.family}, terms={self.n_terms}, "
            f"mode={self.execution_mode}, status={self.status})"
        )


@dataclass
class ProductionPlan:
    project_name: str
    created_at_unix: float
    items: list[ProductionPlanItem]
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_status = {}
        by_family = {}
        for item in self.items:
            by_status[item.status] = by_status.get(item.status, 0) + 1
            by_family[item.family or "unknown"] = by_family.get(item.family or "unknown", 0) + 1
        return (
            "ProductionPlan\n"
            f"  project_name: {self.project_name}\n"
            f"  items: {len(self.items)}\n"
            f"  by_status: {by_status}\n"
            f"  by_family: {by_family}\n"
            f"  warnings: {self.warnings}"
        )


@dataclass
class ProductionRunResult:
    spec: ProductionProjectSpec
    plan: ProductionPlan
    output_dir: str
    artifacts: dict[str, str]
    steps: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            "ProductionRunResult\n"
            f"  project: {self.spec.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  plan_items: {len(self.plan.items)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  steps: {self.steps}\n"
            f"  warnings: {self.warnings}"
        )


def _observable_selection_from_dict(data: dict[str, Any] | None):
    return ObservableSelection(**(data or {}))


def _execution_policy_from_dict(data: dict[str, Any] | None):
    return ExecutionPolicy(**(data or {}))


def _queue_policy_from_dict(data: dict[str, Any] | None):
    return QueuePolicy(**(data or {}))


def _manuscript_from_dict(data: dict[str, Any] | None):
    return ManuscriptSettings(**(data or {}))


def production_spec_from_dict(data: dict[str, Any]) -> ProductionProjectSpec:
    return ProductionProjectSpec(
        project_name=data.get("project_name", "endvqs_production_project"),
        azmqos_version=data.get("azmqos_version", "3.1.0"),
        description=data.get("description", "END/VQS production-run configuration."),
        output_dir=data.get("output_dir", "outputs/endvqs_production_project"),
        component_registry_path=data.get("component_registry_path"),
        term_registry_path=data.get("term_registry_path"),
        observable_selection=_observable_selection_from_dict(data.get("observable_selection")),
        execution_policy=_execution_policy_from_dict(data.get("execution_policy")),
        queue_policy=_queue_policy_from_dict(data.get("queue_policy")),
        manuscript=_manuscript_from_dict(data.get("manuscript")),
        metadata=dict(data.get("metadata", {})),
    )


def load_production_spec(path) -> ProductionProjectSpec:
    path = Path(path)
    spec = production_spec_from_dict(json.loads(path.read_text(encoding="utf-8")))
    spec.metadata.setdefault("config_path", str(path))
    return spec


def save_production_spec(spec: ProductionProjectSpec, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec.to_dict(), indent=2, default=str), encoding="utf-8")
    return path


def init_production_project(output_dir, project_name="endvqs_production_project"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = ProductionProjectSpec(
        project_name=project_name,
        output_dir=str(output_dir),
        metadata={"created_at_unix": time.time(), "source": "init_production_project"},
    )
    config_path = save_production_spec(spec, output_dir / "azmqos_production.json")

    folders = {}
    for name in ["plans", "runs", "database", "dashboard", "manuscript", "archives", "registries"]:
        folder = output_dir / name
        folder.mkdir(exist_ok=True)
        folders[name] = str(folder)

    readme = output_dir / "README_PRODUCTION.md"
    readme.write_text(
        "# AZM-QOS END/VQS Production Project\n\n"
        f"Project: `{project_name}`\n\n"
        "Plan:\n\n"
        "```bash\n"
        f"azmqos production-plan --config {config_path}\n"
        "```\n\n"
        "Run dry-run-safe production workflow:\n\n"
        "```bash\n"
        f"azmqos production-run --config {config_path}\n"
        "```\n",
        encoding="utf-8",
    )

    return spec, {"config_path": str(config_path), "readme": str(readme), "folders": folders}


def validate_production_spec(spec: ProductionProjectSpec) -> list[str]:
    issues = []
    if not spec.project_name:
        issues.append("project_name is empty.")
    if spec.execution_policy.shots <= 0:
        issues.append("execution_policy.shots must be positive.")
    if spec.execution_policy.repeats <= 0:
        issues.append("execution_policy.repeats must be positive.")
    if spec.execution_policy.mode not in {"simulator", "hardware_dry_run", "hardware_submit_disabled"}:
        issues.append("execution_policy.mode must be simulator, hardware_dry_run, or hardware_submit_disabled.")
    if spec.execution_policy.allow_hardware_submit:
        issues.append("allow_hardware_submit=True is blocked in v3.1 production app; use lower-level IBM helpers explicitly.")
    if spec.queue_policy.max_jobs_per_batch <= 0:
        issues.append("queue_policy.max_jobs_per_batch must be positive.")
    if spec.observable_selection.max_components is not None and spec.observable_selection.max_components <= 0:
        issues.append("observable_selection.max_components must be positive or null.")
    return issues


def _read_component_registry(path):
    path = Path(path)
    if not path.exists():
        return {"metadata": {"missing_path": str(path)}, "components": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "components" not in data:
        # Some registries may be direct lists.
        if isinstance(data, list):
            return {"metadata": {}, "components": data}
        return {"metadata": data.get("metadata", {}), "components": []}
    return data


def infer_component_family(component: dict[str, Any]) -> str | None:
    metadata = component.get("metadata") or {}
    if metadata.get("component_family"):
        return str(metadata["component_family"])
    name = str(component.get("name", ""))
    for family in ["Mbb", "Mab", "Maa", "Va", "Vb", "Maa", "Mba"]:
        if name.startswith(family):
            return family
    return None


def select_components_from_registry(registry_data: dict[str, Any], selection: ObservableSelection) -> list[dict[str, Any]]:
    components = list(registry_data.get("components", []))
    selected = []
    excluded = set(selection.exclude_component_names)

    for component in components:
        name = str(component.get("name", "unnamed_component"))
        quantity = str(component.get("quantity", ""))
        family = infer_component_family(component)

        if name in excluded:
            continue
        if selection.include_quantities and quantity not in selection.include_quantities:
            continue
        if selection.families and family not in selection.families:
            continue
        selected.append(component)

    if selection.max_components is not None:
        selected = selected[: selection.max_components]

    return selected


def make_production_plan(spec: ProductionProjectSpec) -> ProductionPlan:
    warnings = validate_production_spec(spec)

    registry_data = {"components": []}
    if spec.component_registry_path:
        registry_data = _read_component_registry(spec.component_registry_path)
        if not registry_data.get("components"):
            warnings.append(f"No components found in component registry: {spec.component_registry_path}")
    elif spec.term_registry_path:
        warnings.append("Term-registry planning is scaffolded; component registry is preferred for family selection.")
    else:
        warnings.append("No component_registry_path or term_registry_path provided.")

    selected = select_components_from_registry(registry_data, spec.observable_selection)

    items = []
    for component in selected:
        name = str(component.get("name", f"component_{len(items)}"))
        quantity = str(component.get("quantity", "unknown"))
        indices = list(component.get("indices", []))
        family = infer_component_family(component)
        terms = component.get("terms", []) or []
        items.append(
            ProductionPlanItem(
                plan_id=str(uuid.uuid4()),
                component_name=name,
                quantity=quantity,
                indices=indices,
                family=family,
                n_terms=len(terms),
                execution_mode=spec.execution_policy.mode,
                backend_name=spec.execution_policy.backend_name,
                shots=spec.execution_policy.shots,
                status="planned",
                metadata={
                    "repeats": spec.execution_policy.repeats,
                    "optimization_level": spec.execution_policy.optimization_level,
                    "allow_hardware_submit": spec.execution_policy.allow_hardware_submit,
                },
            )
        )

    return ProductionPlan(
        project_name=spec.project_name,
        created_at_unix=time.time(),
        items=items,
        warnings=warnings,
        metadata={
            "component_registry_path": spec.component_registry_path,
            "term_registry_path": spec.term_registry_path,
        },
    )


def export_production_plan_json(plan: ProductionPlan, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_name": plan.project_name,
        "created_at_unix": plan.created_at_unix,
        "warnings": plan.warnings,
        "metadata": plan.metadata,
        "items": [asdict(item) for item in plan.items],
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def export_production_plan_csv(plan: ProductionPlan, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "plan_id", "component_name", "quantity", "indices", "family",
            "n_terms", "execution_mode", "backend_name", "shots", "status"
        ])
        for item in plan.items:
            writer.writerow([
                item.plan_id,
                item.component_name,
                item.quantity,
                json.dumps(item.indices),
                item.family,
                item.n_terms,
                item.execution_mode,
                item.backend_name,
                item.shots,
                item.status,
            ])
    return path


def make_production_plan_report(plan: ProductionPlan, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AZM-QOS v3.1 END/VQS Production Plan",
        "",
        "## Summary",
        "",
        "```text",
        plan.summary(),
        "```",
        "",
        "## Plan items",
        "",
    ]
    for item in plan.items:
        lines.extend(["```text", item.summary(), "```", ""])
    if plan.warnings:
        lines.extend(["## Warnings", ""])
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_resume_manifest(plan: ProductionPlan, output_path):
    output_path = Path(output_path)
    payload = {
        "project_name": plan.project_name,
        "created_at_unix": time.time(),
        "resume_policy": "Resume items whose status is planned, pending, failed, or missing_result.",
        "items": [
            {
                "plan_id": item.plan_id,
                "component_name": item.component_name,
                "status": item.status,
                "backend_name": item.backend_name,
                "job_id": item.metadata.get("job_id"),
            }
            for item in plan.items
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return output_path


def make_production_manuscript_scaffold(spec: ProductionProjectSpec, plan: ProductionPlan, artifacts: dict[str, str], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "production_manuscript_scaffold.md"
    tex_path = output_dir / "production_manuscript_scaffold.tex"
    bib_path = output_dir / "references.bib"

    md_lines = [
        f"# {spec.manuscript.title}",
        "",
        "## Abstract",
        "",
        "This manuscript scaffold summarizes an END/VQS production workflow generated by AZM-QOS v3.1.",
        "",
        "## Production plan",
        "",
        f"- Planned components: **{len(plan.items)}**",
        f"- Observable families: `{', '.join(spec.observable_selection.families)}`",
        f"- Execution mode: `{spec.execution_policy.mode}`",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in artifacts.items():
        md_lines.append(f"- **{key}**: `{value}`")
    md_lines.extend([
        "",
        "## Scientific note",
        "",
        "Replace placeholder/template terms with analytically derived END/VQS Pauli decompositions before using production outputs as scientific results.",
        "",
    ])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{hyperref}}
\\title{{{spec.manuscript.title}}}
\\author{{{spec.manuscript.author}}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\begin{{abstract}}
This manuscript scaffold summarizes an END/VQS production workflow generated by AZM-QOS v3.1.
\\end{{abstract}}

\\section{{Production Configuration}}
Observable families: \\texttt{{{", ".join(spec.observable_selection.families)}}}.

Execution mode: \\texttt{{{spec.execution_policy.mode}}}.

Planned components: {len(plan.items)}.

\\section{{Artifacts}}
The production run exported plan files, database records, dashboard artifacts, and a reproducibility archive.

\\section{{Scientific Note}}
Replace placeholder/template terms with analytically derived END/VQS Pauli decompositions before using production outputs as scientific results.

\\end{{document}}
"""
    tex_path.write_text(tex.strip() + "\n", encoding="utf-8")

    if spec.manuscript.include_bibtex:
        bib_path.write_text(
            "@misc{azmqos_v31,\n"
            "  title={AZM-QOS v3.1 END/VQS Production Workflow},\n"
            "  author={AZM-QOS},\n"
            "  year={2026},\n"
            "  note={Reproducible research workflow scaffold}\n"
            "}\n",
            encoding="utf-8",
        )

    return {
        "production_manuscript_markdown": str(md_path),
        "production_manuscript_latex": str(tex_path),
        "production_bibtex": str(bib_path) if spec.manuscript.include_bibtex else "",
    }


def create_production_archive(output_dir, archive_path):
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


def run_production_dry_run(spec_or_path) -> ProductionRunResult:
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    output_dir = Path(spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    warnings = validate_production_spec(spec)
    steps = {}
    artifacts = {}

    # Save resolved config.
    artifacts["production_config"] = str(save_production_spec(spec, output_dir / "azmqos_production_resolved.json"))
    steps["config"] = "saved"

    plan = make_production_plan(spec)
    warnings.extend([w for w in plan.warnings if w not in warnings])

    artifacts["production_plan_json"] = str(export_production_plan_json(plan, output_dir / "plans" / "production_plan.json"))
    artifacts["production_plan_csv"] = str(export_production_plan_csv(plan, output_dir / "plans" / "production_plan.csv"))
    artifacts["production_plan_report"] = str(make_production_plan_report(plan, output_dir / "plans" / "production_plan_report.md"))
    artifacts["resume_manifest"] = str(make_resume_manifest(plan, output_dir / "plans" / "resume_manifest.json"))
    steps["plan"] = f"created {len(plan.items)} plan items"

    # Database records.
    db = ExperimentDatabase(output_dir / "database" / "production_runs.jsonl")
    records = []
    for item in plan.items:
        record = new_run_record(
            name=f"production_{item.component_name}",
            run_type="production_plan_item",
            status="planned",
            tags=["production", item.family or "unknown", item.quantity],
            parameters={
                "component_name": item.component_name,
                "quantity": item.quantity,
                "indices": item.indices,
                "n_terms": item.n_terms,
                "shots": item.shots,
                "execution_mode": item.execution_mode,
            },
            metrics={"n_terms": float(item.n_terms), "shots": float(item.shots)},
            backend=BackendMetadataRecord(
                backend_name=item.backend_name,
                job_status="NOT_SUBMITTED",
                timestamp_unix=time.time(),
            ),
            notes="Dry-run-safe production plan item. No hardware job submitted.",
        )
        db.append(record)
        records.append(record)

    artifacts["production_database_jsonl"] = str(db.path)
    artifacts["production_run_table_csv"] = str(export_run_table_csv(records, output_dir / "database" / "production_run_table.csv"))
    artifacts["production_dashboard_json"] = str(export_dashboard_json(records, output_dir / "database" / "production_dashboard.json"))
    artifacts["production_database_report"] = str(make_run_database_report(records, output_dir / "database" / "production_database_report.md"))
    steps["database"] = f"indexed {len(records)} production records"

    # Dashboard.
    dashboard = build_dashboard_package(output_dir / "dashboard", database_path=db.path)
    artifacts["dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")
    artifacts["artifact_browser_html"] = dashboard.artifacts.get("artifact_browser_html", "")
    steps["dashboard"] = "created"

    # Manuscript scaffold.
    manuscript_artifacts = make_production_manuscript_scaffold(spec, plan, artifacts, output_dir / "manuscript")
    artifacts.update(manuscript_artifacts)
    steps["manuscript"] = "created"

    # Manifest and archive.
    manifest = {
        "package": "AZM-QOS v3.1 END/VQS production dry run",
        "spec": spec.to_dict(),
        "plan_summary": plan.summary(),
        "warnings": warnings,
        "steps": steps,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "production_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    artifacts["production_manifest"] = str(manifest_path)

    archive = create_production_archive(output_dir, output_dir / "archives" / f"{spec.project_name}_production_archive.zip")
    artifacts["production_archive"] = str(archive)
    steps["archive"] = "created"

    return ProductionRunResult(
        spec=spec,
        plan=plan,
        output_dir=str(output_dir),
        artifacts=artifacts,
        steps=steps,
        warnings=warnings,
    )
