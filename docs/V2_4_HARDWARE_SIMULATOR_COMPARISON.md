# AZM-QOS v2.4 Hardware-vs-Simulator Comparison

v2.4 adds comparison tools for IBM hardware-style outputs and simulator outputs.

## New file

```text
azmqos_research/hardware_compare.py
```

## Main features

- Count normalization
- Total variation distance
- Estimator value parsing
- Backend snapshot export
- Hardware-vs-simulator plots
- Markdown and LaTeX reports

## Main command

```bash
azmqos hardware-compare --output-dir outputs/hardware_compare_demo
```

## Main example

```bash
python examples\hardware_comparison_report_demo.py
```
