# AZM-QOS v4.3 Fault-Tolerant Syndrome Circuits and Noise Models

v4.3 adds repeated syndrome-extraction and circuit-level noise scaffolds.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_fault_tolerant.py
```

## Main commands

Standalone demo:

```powershell
azmqos ft-qec-demo --output-dir outputs\ft_qec_demo
```

Production FT-QEC workflow:

```powershell
azmqos production-ft-qec --config outputs\production_project\azmqos_production.json --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Main outputs

- `syndrome_circuit_specs.json`
- `ft_component_results.csv`
- `ft_component_results.json`
- `decoder_comparisons.csv`
- `M_ft_qec_estimates.csv`
- `V_ft_qec_estimates.csv`
- `ft_qec_results.png`
- `ft_qec_report.md`
- `production_ft_qec_manifest.json`
