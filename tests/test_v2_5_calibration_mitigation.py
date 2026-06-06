from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    readout_matrix_from_error,
    mock_calibration_snapshot,
    readout_matrices_from_calibration,
    mitigate_counts_readout,
    zero_noise_extrapolate,
    run_mock_mitigation_workflow,
)
from azmqos_research.cli import main

def test_readout_matrix():
    m = readout_matrix_from_error(0.02, qubit=0)
    arr = m.as_array()
    assert arr.shape == (2, 2)
    assert abs(arr[0, 0] - 0.98) < 1e-12

def test_mitigate_counts():
    cal = mock_calibration_snapshot()
    matrices = readout_matrices_from_calibration(cal, n_qubits=2)
    result = mitigate_counts_readout({"00": 470, "01": 30, "10": 34, "11": 490}, matrices)
    assert abs(sum(result.mitigated_probabilities.values()) - 1.0) < 1e-12

def test_zne():
    result = zero_noise_extrapolate([1.0, 2.0, 3.0], [0.9, 0.8, 0.7], fit_order=1)
    assert result.extrapolated_zero_noise_value > 0.9

def test_mock_mitigation_workflow():
    out_dir = ROOT / "outputs" / "test_v2_5_mitigation"
    result = run_mock_mitigation_workflow(out_dir)
    assert result.mitigated_counts_comparison is not None
    assert Path(result.artifacts["manifest"]).exists()

def test_cli_mitigate():
    out_dir = ROOT / "outputs" / "test_v2_5_cli_mitigate"
    code = main(["mitigate", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "mitigation_manifest.json").exists()

if __name__ == "__main__":
    test_readout_matrix()
    test_mitigate_counts()
    test_zne()
    test_mock_mitigation_workflow()
    test_cli_mitigate()
    print("All v2.5 calibration mitigation tests passed.")
