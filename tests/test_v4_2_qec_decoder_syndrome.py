from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    default_repetition_code,
    repetition_syndrome_for_error,
    repetition_lookup_table,
    decode_repetition_syndrome,
    simulate_syndrome_samples,
    decode_syndrome_samples,
    run_qec_decoder_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qec_decoder,
)
from azmqos_research.cli import main

def test_repetition_syndromes():
    assert repetition_syndrome_for_error(None, 3) == "00"
    assert repetition_syndrome_for_error(0, 3) == "10"
    assert repetition_syndrome_for_error(1, 3) == "11"
    assert repetition_syndrome_for_error(2, 3) == "01"

def test_lookup_decoder():
    table = repetition_lookup_table(3)
    assert table["00"] == "none"
    assert decode_repetition_syndrome("10", 3) == "X0"

def test_sample_and_decode():
    code = default_repetition_code(3)
    samples = simulate_syndrome_samples("test_component", code, shots=16, physical_error_rate=0.2)
    decoded = decode_syndrome_samples(samples, code)
    assert len(samples) == 16
    assert len(decoded) == 16

def test_qec_decoder_demo():
    out_dir = ROOT / "outputs" / "test_v4_2_decoder_demo"
    result = run_qec_decoder_demo(out_dir)
    assert len(result.decoded_estimates) == 1
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_qec_decoder():
    spec, artifacts = _prepared_spec("test_v4_2_production_decoder")
    result = run_production_qec_decoder(
        artifacts["config_path"],
        code_name="repetition3",
        max_components=2,
        shots=64,
        physical_error_rate=0.05,
    )
    assert len(result.decoded_estimates) == 2
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["M_decoded_logical_estimates_csv"]).exists()

def test_cli_decoder_commands():
    out_dir = ROOT / "outputs" / "test_v4_2_cli_decoder_demo"
    code = main(["qec-decoder-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "qec_decoder_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_2_cli_production_decoder")
    code = main([
        "production-qec-decode",
        "--config", artifacts["config_path"],
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--physical-error-rate", "0.05",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "qec_decoder" / "production_qec_decoder_manifest.json").exists()

if __name__ == "__main__":
    test_repetition_syndromes()
    test_lookup_decoder()
    test_sample_and_decode()
    test_qec_decoder_demo()
    test_production_qec_decoder()
    test_cli_decoder_commands()
    print("All v4.2 QEC decoder/syndrome tests passed.")
