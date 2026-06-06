from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
import json
from azmqos_research import load_backend_calibration, default_calibration_metadata

print("AZM-QOS v4.7 Calibration Metadata Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "calibration_metadata_demo"
out_dir.mkdir(parents=True, exist_ok=True)
cal_path = out_dir / "backend_calibration.json"
cal_path.write_text(json.dumps({
    "backend_name": "ibm_fez",
    "source": "example_import",
    "median_readout_error": 0.018,
    "median_cx_error": 0.012,
    "median_t1_us": 180.0,
    "median_t2_us": 140.0,
    "n_qubits": 156
}, indent=2), encoding="utf-8")

print("Default:")
print(default_calibration_metadata("ibm_fez").summary())
print()
print("Imported:")
print(load_backend_calibration(cal_path).summary())
