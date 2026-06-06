from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import platform
import time
import uuid
import sys

@dataclass
class ExperimentManifest:
    experiment_id: str
    name: str
    azmqos_version: str
    created_at_unix: float
    python_version: str
    platform: str
    configuration: dict[str, Any]
    artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"ExperimentManifest(id={self.experiment_id}, name={self.name}, "
            f"version={self.azmqos_version}, artifacts={len(self.artifacts)})"
        )

    def to_dict(self):
        return asdict(self)

def create_experiment_manifest(name: str, configuration: dict[str, Any] | None = None, **metadata):
    return ExperimentManifest(
        experiment_id=str(uuid.uuid4()),
        name=name,
        azmqos_version="2.0.0",
        created_at_unix=time.time(),
        python_version=sys.version,
        platform=platform.platform(),
        configuration=configuration or {},
        metadata=metadata,
    )

def save_manifest_json(manifest: ExperimentManifest, path):
    path = Path(path)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path
