from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    load_registry_for_research,
    run_endvqs_shot_scaling_package,
    build_publication_figure_package,
    caption_for_m_matrix,
    save_captions,
)

def test_caption_generation():
    out_dir = ROOT / "outputs" / "test_v2_2_captions"
    artifacts = save_captions([caption_for_m_matrix()], out_dir)
    assert Path(artifacts["markdown"]).exists()
    assert Path(artifacts["latex"]).exists()

def test_shot_scaling_package():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    load_result = load_registry_for_research(component_registry_json=template)
    out_dir = ROOT / "outputs" / "test_v2_2_shot_scaling"
    result, artifacts = run_endvqs_shot_scaling_package(
        load_result.registry,
        output_dir=out_dir,
        shot_powers=(6, 8),
        repeats=2,
        seed=1,
    )
    assert len(result.points) == 2
    assert Path(artifacts["shot_scaling_csv"]).exists()

def test_publication_package():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    out_dir = ROOT / "outputs" / "test_v2_2_publication_package"
    package = build_publication_figure_package(
        output_dir=out_dir,
        component_registry_json=template,
        shots=64,
        repeats=1,
        n_rounds=3,
        n_trials=3,
        shot_powers=(6, 8),
        seed=1,
    )
    assert Path(package.artifacts["publication_manifest"]).exists()
    assert Path(package.artifacts["table_m_matrix"]).exists()

if __name__ == "__main__":
    test_caption_generation()
    test_shot_scaling_package()
    test_publication_package()
    print("All v2.2 publication-plot tests passed.")
