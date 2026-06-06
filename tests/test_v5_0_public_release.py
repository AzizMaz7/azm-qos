from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    PUBLIC_VERSION,
    make_public_release_manifest,
    export_api_reference_markdown,
    run_public_release_info,
    run_public_release_validate,
)
from azmqos_research.cli import main

def test_manifest():
    manifest = make_public_release_manifest()
    assert manifest.version == PUBLIC_VERSION
    assert len(manifest.entry_points) >= 5

def test_api_reference_export():
    out = ROOT / "outputs" / "test_v5_0_api_reference" / "api_reference.md"
    path = export_api_reference_markdown(out)
    assert path.exists()
    assert "qec_public_release" in path.read_text(encoding="utf-8")

def test_public_release_info_and_validate():
    out = ROOT / "outputs" / "test_v5_0_public_info"
    artifacts = run_public_release_info(out)
    assert Path(artifacts["public_release_manifest"]).exists()
    assert Path(artifacts["api_reference"]).exists()
    validation = run_public_release_validate(ROOT / "outputs" / "test_v5_0_public_validate", package_root=ROOT)
    assert Path(validation["validation_report"]).exists()
    assert validation["ok"] is True

def test_cli_public_release_commands():
    info_out = ROOT / "outputs" / "test_v5_0_cli_info"
    code = main(["public-release-info", "--output-dir", str(info_out)])
    assert code == 0
    assert (info_out / "public_release_manifest.json").exists()

    val_out = ROOT / "outputs" / "test_v5_0_cli_validate"
    code = main(["public-release-validate", "--output-dir", str(val_out)])
    assert code == 0
    assert (val_out / "public_release_validation.md").exists()

if __name__ == "__main__":
    test_manifest()
    test_api_reference_export()
    test_public_release_info_and_validate()
    test_cli_public_release_commands()
    print("All v5.0 public release tests passed.")
