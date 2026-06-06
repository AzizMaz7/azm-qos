from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from azmqos import (
    PauliTerm,
    expectation_value,
    RuntimeManager,
    RuntimeConfig,
    default_plugin_registry,
    PluginRegistry,
    VQSPlugin,
)
from azmqos.states import zero_state

def test_z_zero():
    assert np.isclose(expectation_value(zero_state(1), PauliTerm(1, "Z")), 1.0)

def test_default_plugins_exist():
    registry = default_plugin_registry()
    names = registry.list_plugins()
    assert "azmqos-vqs-template" in names
    assert "azmqos-endvqs-template" in names
    assert "azmqos-qec-template" in names

def test_vqs_plugin_workloads_run():
    registry = default_plugin_registry()
    workloads = registry.create_workloads("azmqos-vqs-template")
    assert len(workloads) == 2
    result = RuntimeManager().run(workloads[0], "shot_simulator", RuntimeConfig(shots=128, repeats=2, seed=1))
    assert result.backend_type == "shot_simulator"

def test_qec_plugin_exact():
    registry = default_plugin_registry()
    workload = registry.create_workloads("azmqos-qec-template", state="bell")
    result = RuntimeManager().run(workload, "local_statevector", RuntimeConfig())
    assert abs(result.term_estimates["stabilizer_ZZ"] - 1.0) < 1e-8

def test_custom_registry():
    registry = PluginRegistry()
    registry.register(VQSPlugin())
    assert "azmqos-vqs-template" in registry.list_plugins()

if __name__ == "__main__":
    test_z_zero()
    test_default_plugins_exist()
    test_vqs_plugin_workloads_run()
    test_qec_plugin_exact()
    test_custom_registry()
    print("All v0.6 direct tests passed.")
