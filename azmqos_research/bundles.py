from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import zipfile
import json

@dataclass
class ReproducibilityBundle:
    bundle_path: str
    artifact_count: int
    manifest_path: str

    def summary(self):
        return f"ReproducibilityBundle(path={self.bundle_path}, artifacts={self.artifact_count})"

def create_reproducibility_bundle(output_dir, bundle_path, manifest):
    output_dir = Path(output_dir)
    bundle_path = Path(bundle_path)
    if bundle_path.exists():
        bundle_path.unlink()

    artifact_paths = []
    for p in output_dir.rglob("*"):
        if p.is_file() and p.resolve() != bundle_path.resolve():
            artifact_paths.append(p)

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in artifact_paths:
            z.write(p, arcname=p.relative_to(output_dir))

    return ReproducibilityBundle(
        bundle_path=str(bundle_path),
        artifact_count=len(artifact_paths),
        manifest_path=manifest.artifacts.get("manifest_json", ""),
    )
