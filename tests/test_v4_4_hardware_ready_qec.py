from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    get_code_by_name,
    default_backend_target,
    make_repeated_syndrome_schedule,
    resource_summary_from_spec,
    transpile_syndrome_spec_dry_run,
    check_isa_constraints,
    recommend_noise_aware_layout,
    make_hardware_dry_run_job_manifest,
    run_qec_hardware_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qec_hardware_dry_run,
)
from azmqos_research.cli import main

def test_resource_and_isa():
    code = get_code_by_name("repetition3")
    backend = default_backend_target("ibm_fez")
    spec = make_repeated_syndrome_schedule(code, rounds=1)[0]
    summary = resource_summary_from_spec(spec)
    assert summary.n_qubits >= code.n_physical
    isa = check_isa_constraints(summary, backend)
    assert isinstance(isa.passed, bool)

def test_transpile_dry_run_and_manifest():
    code = get_code_by_name("repetition3")
    backend = default_backend_target("ibm_fez")
    spec = make_repeated_syndrome_schedule(code, rounds=1)[0]
    summary = transpile_syndrome_spec_dry_run(spec, backend)
    isa = check_isa_constraints(summary, backend)
    manifest = make_hardware_dry_run_job_manifest(summary, isa, backend, shots=64)
    assert manifest.job_id.startswith("AZMQOS-DRYRUN-")
    assert manifest.submitted is False

def test_layout_recommendation():
    code = get_code_by_name("repetition3")
    backend = default_backend_target("ibm_fez")
    layout = recommend_noise_aware_layout(code, backend)
    assert len(layout.physical_qubits) == code.n_physical
    assert len(layout.ancilla_qubits) == len(code.stabilizers)

def test_qec_hardware_demo():
    out_dir = ROOT / "outputs" / "test_v4_4_hardware_demo"
    result = run_qec_hardware_demo(out_dir, backend_name="ibm_fez", code_name="repetition3", rounds=2, shots=64)
    assert len(result.resources) == 2 * len(result.code.stabilizers)
    assert Path(result.artifacts["manifest"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_qec_hardware_dry_run():
    spec, artifacts = _prepared_spec("test_v4_4_production_hardware")
    result = run_production_qec_hardware_dry_run(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=2,
        shots=64,
        rounds=2,
    )
    assert len(result.job_manifests) == 2 * len(result.code.stabilizers)
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["job_manifests_json"]).exists()

def test_cli_hardware_commands():
    out_dir = ROOT / "outputs" / "test_v4_4_cli_hardware_demo"
    code = main([
        "qec-hardware-demo",
        "--output-dir", str(out_dir),
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--rounds", "2",
        "--shots", "64",
    ])
    assert code == 0
    assert (out_dir / "qec_hardware_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_4_cli_production_hardware")
    code = main([
        "production-qec-hardware-dry-run",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "2",
        "--shots", "64",
        "--rounds", "2",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "qec_hardware_dry_run" / "production_qec_hardware_dry_run_manifest.json").exists()

if __name__ == "__main__":
    test_resource_and_isa()
    test_transpile_dry_run_and_manifest()
    test_layout_recommendation()
    test_qec_hardware_demo()
    test_production_qec_hardware_dry_run()
    test_cli_hardware_commands()
    print("All v4.4 hardware-ready QEC tests passed.")
