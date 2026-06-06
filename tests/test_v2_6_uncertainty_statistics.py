from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    binomial_standard_error,
    wilson_confidence_interval,
    counts_uncertainty,
    expectation_from_counts,
    bootstrap_expectation_uncertainty,
    parity_observable_map,
    propagate_difference_uncertainty,
    run_mock_uncertainty_workflow,
)
from azmqos_research.cli import main

def test_binomial_standard_error():
    se = binomial_standard_error(0.5, 100)
    assert abs(se - 0.05) < 1e-12

def test_wilson_interval():
    ci = wilson_confidence_interval(50, 100)
    assert 0.0 <= ci.lower <= ci.upper <= 1.0
    assert ci.method == "wilson"

def test_counts_uncertainty():
    result = counts_uncertainty({"0": 50, "1": 50})
    assert result.shots == 100
    assert len(result.bitstrings) == 2

def test_expectation_from_counts():
    value = expectation_from_counts({"00": 5, "11": 5}, {"00": 1.0, "11": 1.0})
    assert abs(value - 1.0) < 1e-12

def test_bootstrap_expectation_uncertainty():
    obs = parity_observable_map(2)
    result = bootstrap_expectation_uncertainty({"00": 50, "01": 50}, obs, n_bootstrap=50, seed=1)
    assert result.shots == 100
    assert result.interval.lower <= result.estimate <= result.interval.upper

def test_difference_uncertainty():
    result = propagate_difference_uncertainty(1.0, 0.01, 0.9, 0.02)
    assert result.combined_standard_error > 0
    assert result.difference < 0

def test_mock_uncertainty_workflow():
    out_dir = ROOT / "outputs" / "test_v2_6_uncertainty"
    result = run_mock_uncertainty_workflow(out_dir, n_bootstrap=50, seed=1)
    assert result.expectation_difference_uncertainty is not None
    assert Path(result.artifacts["manifest"]).exists()

def test_cli_uncertainty():
    out_dir = ROOT / "outputs" / "test_v2_6_cli_uncertainty"
    code = main(["uncertainty", "--output-dir", str(out_dir), "--bootstrap", "50"])
    assert code == 0
    assert (out_dir / "uncertainty_manifest.json").exists()

if __name__ == "__main__":
    test_binomial_standard_error()
    test_wilson_interval()
    test_counts_uncertainty()
    test_expectation_from_counts()
    test_bootstrap_expectation_uncertainty()
    test_difference_uncertainty()
    test_mock_uncertainty_workflow()
    test_cli_uncertainty()
    print("All v2.6 uncertainty statistics tests passed.")
