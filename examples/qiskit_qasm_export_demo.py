from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos.qiskit_adapter import qiskit_available, export_circuit_openqasm

if not qiskit_available():
    print("Qiskit is not installed.")
    print("Install it with: python -m pip install qiskit qiskit-aer")
    raise SystemExit(0)

from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

out = ROOT / "outputs"
out.mkdir(exist_ok=True)
qasm_path = out / "bell_circuit.qasm"
qasm_text = export_circuit_openqasm(qc, qasm_path)

print("Exported QASM to:", qasm_path)
print(qasm_text[:500])
