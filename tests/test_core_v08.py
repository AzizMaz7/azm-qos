from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from azmqos import RuntimeManager, RuntimeConfig, default_plugin_registry
from azmqos_endvqs import (
    default_endvqs_registry,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
    run_endvqs_benchmark,
    ENDVQSWorkloadPlugin,
)
from azmqos import PluginRegistry

def test_registry_dimension():
    registry = default_endvqs_registry()
    assert registry.dimension == 2

def test_build_workloads():
    workloads = build_all_endvqs_workloads()
    assert len(workloads) == 6  # 2x2 M entries + 2 V entries

def test_m_v_assembly():
    registry = default_endvqs_registry()
    workloads = build_all_endvqs_workloads(registry=registry)
    manager = RuntimeManager()
    results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=128, repeats=2, seed=1)) for w in workloads]
    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)
    assert M.shape == (2, 2)
    assert V.shape == (2,)

def test_benchmark_runs():
    data = run_endvqs_benchmark(shots=128, repeats=2, seed=1)
    assert data["M"].shape == (2, 2)
    assert data["V"].shape == (2,)

def test_plugin_registry():
    registry = PluginRegistry()
    registry.register(ENDVQSWorkloadPlugin())
    assert "azmqos-endvqs-v08" in registry.list_plugins()

def test_default_registry_includes_v08_plugin():
    registry = default_plugin_registry()
    assert "azmqos-endvqs-v08" in registry.list_plugins()

if __name__ == "__main__":
    test_registry_dimension()
    test_build_workloads()
    test_m_v_assembly()
    test_benchmark_runs()
    test_plugin_registry()
    test_default_registry_includes_v08_plugin()
    print("All v0.8 direct tests passed.")
