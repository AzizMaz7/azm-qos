from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    extract_sampler_counts,
    compare_counts,
    IBMHardwareResult,
)

def test_extract_sampler_counts_from_dict():
    counts = extract_sampler_counts({"counts": {"00": 5, "11": 7}})
    assert counts == {"00": 5, "11": 7}

def test_extract_sampler_counts_direct_dict():
    counts = extract_sampler_counts({"00": 5, "11": 7})
    assert counts == {"00": 5, "11": 7}

def test_hardware_result_container():
    result = IBMHardwareResult(
        job_id="demo",
        backend_name="ibm_demo",
        status="DONE",
        counts={"00": 5, "11": 7},
    )
    assert "demo" in result.summary()
    assert result.counts["11"] == 7

def test_compare_counts_with_extracted_counts():
    hardware_counts = extract_sampler_counts({"counts": {"00": 8, "11": 2}})
    comparison = compare_counts({"00": 10}, hardware_counts)
    assert comparison.total_variation_distance > 0

if __name__ == "__main__":
    test_extract_sampler_counts_from_dict()
    test_extract_sampler_counts_direct_dict()
    test_hardware_result_container()
    test_compare_counts_with_extracted_counts()
    print("All v2.4 updated IBM result helper tests passed.")
