from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import time


@dataclass
class WorkflowSettings:
    mode: str = "mock"
    run_local_research: bool = True
    run_mitigation: bool = True
    run_uncertainty: bool = True
    run_sync: bool = True
    build_dashboard: bool = True
    export_manuscript: bool = True
    create_final_archive: bool = True


@dataclass
class HardwareSettings:
    submit_real_jobs: bool = False
    backend_name: str | None = None
    job_id: str | None = None
    shots: int = 1024


@dataclass
class AZMQOSProjectConfig:
    project_name: str
    azmqos_version: str = "3.0.0"
    description: str = "AZM-QOS integrated research project."
    output_dir: str = "outputs/azmqos_project"
    workflow: WorkflowSettings = field(default_factory=WorkflowSettings)
    hardware: HardwareSettings = field(default_factory=HardwareSettings)
    simulator_counts: dict[str, int] = field(default_factory=lambda: {"00": 510, "11": 514})
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "AZMQOSProjectConfig\n"
            f"  project_name: {self.project_name}\n"
            f"  version: {self.azmqos_version}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  mode: {self.workflow.mode}\n"
            f"  submit_real_jobs: {self.hardware.submit_real_jobs}"
        )

    def to_dict(self):
        return asdict(self)


def default_project_config(output_dir="outputs/azmqos_project", project_name="azmqos_research_project"):
    return AZMQOSProjectConfig(
        project_name=project_name,
        output_dir=str(output_dir),
        metadata={"created_at_unix": time.time(), "source": "default_project_config"},
    )


def _workflow_from_dict(data: dict[str, Any] | None):
    return WorkflowSettings(**(data or {}))


def _hardware_from_dict(data: dict[str, Any] | None):
    return HardwareSettings(**(data or {}))


def project_config_from_dict(data: dict[str, Any]) -> AZMQOSProjectConfig:
    return AZMQOSProjectConfig(
        project_name=data.get("project_name", "azmqos_research_project"),
        azmqos_version=data.get("azmqos_version", "3.0.0"),
        description=data.get("description", "AZM-QOS integrated research project."),
        output_dir=data.get("output_dir", "outputs/azmqos_project"),
        workflow=_workflow_from_dict(data.get("workflow")),
        hardware=_hardware_from_dict(data.get("hardware")),
        simulator_counts={str(k): int(v) for k, v in data.get("simulator_counts", {"00": 510, "11": 514}).items()},
        metadata=dict(data.get("metadata", {})),
    )


def load_project_config(path) -> AZMQOSProjectConfig:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    cfg = project_config_from_dict(data)
    cfg.metadata.setdefault("config_path", str(path))
    return cfg


def save_project_config(config: AZMQOSProjectConfig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_dict(), indent=2, default=str), encoding="utf-8")
    return path


def init_project(output_dir, project_name="azmqos_research_project"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = default_project_config(output_dir=output_dir, project_name=project_name)
    config_path = save_project_config(config, output_dir / "azmqos_project.json")

    folders = {}
    for name in ["raw", "analysis", "dashboard", "reports", "archives", "registry"]:
        folder = output_dir / name
        folder.mkdir(exist_ok=True)
        folders[name] = str(folder)

    readme = output_dir / "README_AZMQOS_PROJECT.md"
    readme.write_text(
        "# AZM-QOS Project\n\n"
        f"Project name: `{project_name}`\n\n"
        "Run:\n\n"
        "```bash\n"
        f"azmqos app-run --config {config_path}\n"
        "```\n",
        encoding="utf-8",
    )

    return config, {
        "config_path": str(config_path),
        "readme": str(readme),
        "folders": folders,
    }


def validate_project_config(config: AZMQOSProjectConfig) -> list[str]:
    issues = []
    if not config.project_name:
        issues.append("project_name is empty.")
    if config.workflow.mode not in {"mock", "local", "hardware_safe"}:
        issues.append("workflow.mode should be one of: mock, local, hardware_safe.")
    if config.hardware.submit_real_jobs:
        issues.append("submit_real_jobs=True is not handled by the v3.0 integrated app; use lower-level IBM helpers explicitly.")
    if config.hardware.shots <= 0:
        issues.append("hardware.shots must be positive.")
    if not config.simulator_counts:
        issues.append("simulator_counts is empty.")
    return issues
