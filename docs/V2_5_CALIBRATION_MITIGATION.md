# AZM-QOS v2.5 Calibration-Aware Mitigation

v2.5 adds calibration-aware mitigation scaffolds on top of the updated v2.4 hardware-comparison package.

## New file

```text
azmqos_research/calibration_mitigation.py
```

## Main features

- Readout mitigation matrices
- Tensor-product readout mitigation
- Calibration snapshots
- Zero-noise extrapolation scaffold
- Mitigated counts comparison
- Mitigation reports
- Integration with flexible IBM result retrieval from `ibm_results.py`

## Main command

```bash
azmqos mitigate --output-dir outputs/mitigation_demo
```

## Main examples

```bash
python examples\readout_mitigation_demo.py
python examples\zne_demo.py
python examples\mitigated_hardware_comparison_demo.py
python examples\latest_hardware_mitigation_demo.py
```

For the latest visible hardware job from any backend:

```python
from azmqos_research import run_latest_hardware_mitigation_workflow

result = run_latest_hardware_mitigation_workflow(
    output_dir="outputs/latest_mitigated",
    simulator_counts={"00": 510, "11": 514},
    backend_name=None,
)
```
