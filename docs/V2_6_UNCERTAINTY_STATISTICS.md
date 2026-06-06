# AZM-QOS v2.6 Uncertainty Propagation and Statistical Confidence

v2.6 adds finite-shot uncertainty tools.

## New file

```text
azmqos_research/uncertainty.py
```

## Main features

- Binomial standard error
- Wilson confidence intervals
- Bootstrap expectation intervals
- Error propagation for simulator-hardware differences
- Count probability uncertainty tables
- Uncertainty reports

## Main command

```bash
azmqos uncertainty --output-dir outputs/uncertainty_demo
```

## Main examples

```bash
python examples\uncertainty_counts_demo.py
python examples\expectation_uncertainty_demo.py
python examples\uncertainty_report_demo.py
```
