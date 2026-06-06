from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json
from .workload import QuantumWorkload

@dataclass
class QuantumProject:
    name: str
    workloads: list[QuantumWorkload] = field(default_factory=list)
    domain: str = "general"
    owner: str | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_workload(self, workload):
        self.workloads.append(workload)

    def summary(self):
        lines = [
            f"QuantumProject: {self.name}",
            f"Domain: {self.domain}",
            f"Workloads: {len(self.workloads)}",
        ]
        for i, w in enumerate(self.workloads, 1):
            lines.append(f"  {i}. {w.name} | domain={w.domain} | qubits={w.n_qubits} | observables={len(w.observables)}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            "name": self.name,
            "domain": self.domain,
            "owner": self.owner,
            "description": self.description,
            "metadata": self.metadata,
            "workloads": [w.to_dict() for w in self.workloads],
        }

    def save_manifest(self, path):
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path
