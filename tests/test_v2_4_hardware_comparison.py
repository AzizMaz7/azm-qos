from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    normalize_counts,
    total_variation_distance,
    compare_counts,
    compare_expectation_values,
    parse_counts_from_runtime_result,
    parse_estimator_value,
    run_mock_hardware_comparison,
)
from azmqos_research.cli import main

def test_normalize_counts():
    p = normalize_counts({"0": 3, "1": 1})
    assert abs(p["0"] - 0.75) < 1e-12

def test_tvd():
    p = {"0": 1.0}
    q = {"1": 1.0}
    assert abs(total_variation_distance(p, q) - 1.0) < 1e-12

def test_compare_counts():
    c = compare_counts({"00": 10}, {"00": 8, "11": 2})
    assert c.shots_simulator == 10
    assert c.shots_hardware == 10
    assert c.total_variation_distance > 0

def test_expectation_comparison():
    e = compare_expectation_values(1.0, 0.9)
    assert abs(e.absolute_error - 0.1) < 1e-12

def test_parsers():
    counts = parse_counts_from_runtime_result({"counts": {"00": 4, "11": 6}})
    assert counts["11"] == 6
    value = parse_estimator_value({"values": [0.5]})
    assert value == 0.5

def test_mock_hardware_comparison():
    out_dir = ROOT / "outputs" / "test_v2_4_mock_hardware"
    result = run_mock_hardware_comparison(out_dir)
    assert result.counts_comparison.total_variation_distance >= 0
    assert Path(result.artifacts["manifest"]).exists()

def test_cli_hardware_compare():
    out_dir = ROOT / "outputs" / "test_v2_4_cli_hardware"
    code = main(["hardware-compare", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "hardware_comparison_manifest.json").exists()

if __name__ == "__main__":
    test_normalize_counts()
    test_tvd()
    test_compare_counts()
    test_expectation_comparison()
    test_parsers()
    test_mock_hardware_comparison()
    test_cli_hardware_compare()
    print("All v2.4 hardware comparison tests passed.")
