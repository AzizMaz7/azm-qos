from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import BackendSnapshot, save_backend_snapshot

print("AZM-QOS v2.4 Backend Snapshot Demo")
print("=" * 70)

snapshot = BackendSnapshot(
    backend_name="mock_ibm_backend",
    num_qubits=127,
    basis_gates=["rz", "sx", "x", "cx", "measure"],
    coupling_map=None,
    backend_version="mock",
    properties_summary={"t1_median_us": "mock", "readout_error_median": "mock"},
)

out_dir = ROOT / "outputs" / "backend_snapshot_demo"
out_dir.mkdir(parents=True, exist_ok=True)
path = save_backend_snapshot(snapshot, out_dir / "backend_snapshot.json")

print(snapshot.summary())
print("Saved:", path)
