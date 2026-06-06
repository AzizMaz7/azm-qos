from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import (
    default_endvqs_registry,
    save_term_registry_json,
    load_term_registry_json,
    save_term_registry_csv,
    load_term_registry_csv,
    validate_term_registry,
    default_component_registry_from_proxy_terms,
    component_registry_to_term_registry,
    load_component_registry_json,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
)

def test_json_roundtrip():
    path = ROOT / "outputs" / "test_registry_roundtrip.json"
    path.parent.mkdir(exist_ok=True)
    registry = default_endvqs_registry()
    save_term_registry_json(registry, path)
    loaded = load_term_registry_json(path)
    assert validate_term_registry(loaded).ok

def test_csv_roundtrip():
    path = ROOT / "outputs" / "test_registry_roundtrip.csv"
    path.parent.mkdir(exist_ok=True)
    registry = default_endvqs_registry()
    save_term_registry_csv(registry, path)
    loaded = load_term_registry_csv(path)
    assert validate_term_registry(loaded).ok

def test_component_conversion():
    comp = default_component_registry_from_proxy_terms()
    registry = component_registry_to_term_registry(comp)
    assert validate_term_registry(registry).ok

def test_template_load_and_run():
    template_path = ROOT / "templates" / "endvqs_real_terms_template.json"
    comp = load_component_registry_json(template_path)
    registry = component_registry_to_term_registry(comp)
    assert validate_term_registry(registry).ok
    workloads = build_all_endvqs_workloads(registry=registry)
    manager = RuntimeManager()
    results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=64, repeats=1, seed=1)) for w in workloads]
    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)
    assert M.shape == (2, 2)
    assert V.shape == (2,)

if __name__ == "__main__":
    test_json_roundtrip()
    test_csv_roundtrip()
    test_component_conversion()
    test_template_load_and_run()
    print("All v1.1 END/VQS registry tests passed.")
