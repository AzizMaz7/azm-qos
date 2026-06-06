# AZM-QOS v4.7 Hardware Analysis Reports and Final QEC Experiment Archives

v4.7 adds hardware-analysis reporting and final QEC experiment archives.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_hardware_analysis.py
```

## Main commands

Standalone demo:

```powershell
azmqos hardware-analysis-demo --output-dir outputs\hardware_analysis_demo --backend-name ibm_fez
```

Production analysis workflow:

```powershell
azmqos production-hardware-analysis --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Main outputs

- `hardware_run_summary.json`
- `calibration_metadata.json`
- `counts_confidence_intervals.csv`
- `logical_failure_bands.csv`
- `logical_failure_bands.png`
- `real_vs_synthetic_summary.png`
- `hardware_analysis_report.md`
- `production_hardware_analysis_manifest.json`
- final QEC experiment archive ZIP
