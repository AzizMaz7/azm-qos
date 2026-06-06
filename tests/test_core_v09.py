from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig, default_plugin_registry, PluginRegistry
from azmqos_qec import (
    repetition_code_3,
    bell_stabilizer_code,
    build_all_qec_workloads,
    build_stabilizer_workloads,
    infer_syndrome_from_stabilizers,
    MajorityVoteRepetitionDecoder,
    estimate_qec_resources,
    default_logical_observables,
    QECWorkloadPlugin,
)

def test_qec_code_specs():
    assert repetition_code_3().n_physical_qubits == 3
    assert bell_stabilizer_code().n_physical_qubits == 2

def test_qec_workloads_run():
    code = repetition_code_3()
    workload_set = build_all_qec_workloads(code)
    assert len(workload_set.stabilizer_workloads) == 2
    result = RuntimeManager().run(workload_set.stabilizer_workloads[0], "local_statevector", RuntimeConfig())
    assert result.backend_type == "statevector"

def test_syndrome_decoder():
    code = repetition_code_3()
    workloads = build_stabilizer_workloads(code)
    manager = RuntimeManager()
    results = [manager.run(w, "local_statevector", RuntimeConfig()) for w in workloads]
    syndrome = infer_syndrome_from_stabilizers(results)
    decoded = MajorityVoteRepetitionDecoder().decode(syndrome)
    assert decoded.correction == "I"

def test_resource_estimate():
    code = repetition_code_3()
    logicals = default_logical_observables(code.name)
    est = estimate_qec_resources(code, logicals, shots_per_circuit=100, rounds=2)
    assert est.estimated_total_shots > 0

def test_plugin_registry_qec():
    registry = PluginRegistry()
    registry.register(QECWorkloadPlugin())
    assert "azmqos-qec-v09" in registry.list_plugins()

def test_default_registry_includes_qec_v09():
    registry = default_plugin_registry()
    assert "azmqos-qec-v09" in registry.list_plugins()

if __name__ == "__main__":
    test_qec_code_specs()
    test_qec_workloads_run()
    test_syndrome_decoder()
    test_resource_estimate()
    test_plugin_registry_qec()
    test_default_registry_includes_qec_v09()
    print("All v0.9 direct tests passed.")
