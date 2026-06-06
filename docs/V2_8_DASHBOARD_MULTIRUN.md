# AZM-QOS v2.8 Dashboard and Multi-Run Analysis

v2.8 adds dashboard-ready multi-run analysis.

## New file

```text
azmqos_research/dashboard.py
```

## Main outputs

- `dashboard.html`
- `artifact_browser.html`
- `dashboard.json`
- `run_table.csv`
- `backend_history.csv`
- metric trend CSV files
- metric trend figures
- `dashboard_report.md`

## Main command

```bash
azmqos dashboard-demo --output-dir outputs/dashboard_demo
```

## Main examples

```bash
python examples\dashboard_demo.py
python examples\metric_trend_demo.py
python examples\artifact_browser_demo.py
```
