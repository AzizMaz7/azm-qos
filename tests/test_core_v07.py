from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import (
    RuntimeManager,
    BackendSelector,
    BackendSelectionRequest,
    make_generic_two_qubit_workload,
    ibm_runtime_available,
    diagnose_ibm_runtime,
)

def test_ibm_availability_function():
    value = ibm_runtime_available()
    assert isinstance(value, bool)

def test_ibm_diagnostics():
    diag = diagnose_ibm_runtime()
    assert hasattr(diag, "runtime_package_available")
    assert hasattr(diag, "message")

def test_ibm_backend_registered():
    manager = RuntimeManager()
    assert "ibm_runtime" in manager.list_backends()

def test_backend_selector_exact():
    manager = RuntimeManager()
    workload = make_generic_two_qubit_workload()
    selection = BackendSelector().select(manager, workload, BackendSelectionRequest(require_exact=True))
    assert selection.backend_name == "local_statevector"

def test_backend_selector_cloud():
    manager = RuntimeManager()
    workload = make_generic_two_qubit_workload()
    selection = BackendSelector().select(manager, workload, BackendSelectionRequest(allow_cloud=True, prefer_hardware=True))
    assert selection.backend_name == "ibm_runtime"

if __name__ == "__main__":
    test_ibm_availability_function()
    test_ibm_diagnostics()
    test_ibm_backend_registered()
    test_backend_selector_exact()
    test_backend_selector_cloud()
    print("All v0.7 direct tests passed.")
