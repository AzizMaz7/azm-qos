from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import PauliTerm, RuntimeManager, RuntimeConfig
from azmqos.qiskit_adapter import qiskit_available, make_qiskit_circuit_workload

if not qiskit_available():
    print("Qiskit is not installed.")
    print("Install it with: python -m pip install qiskit qiskit-aer")
    raise SystemExit(0)

from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

workload = make_qiskit_circuit_workload(
    circuit=qc,
    observables=[
        PauliTerm(1.0, "ZZ", label="bell_ZZ"),
        PauliTerm(1.0, "XX", label="bell_XX"),
    ],
    name="bell_state_qiskit_workload",
    domain="qiskit_demo",
)

manager = RuntimeManager()
if "qiskit_aer" not in manager.list_backends():
    print("Qiskit Aer backend was not registered.")
    print("Install qiskit-aer with: python -m pip install qiskit-aer")
    raise SystemExit(0)

result = manager.run(workload, "qiskit_aer", RuntimeConfig(shots=4096, repeats=5, seed=123))
print(result.summary())
print(result.term_estimates)
