# AZM-QOS v4.2 QEC Decoder and Syndrome Post-Processing

v4.2 adds decoder and syndrome post-processing scaffolds.

## Required first production command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## New file

```text
azmqos_research/qec_decoder.py
```

## Main commands

Standalone demo:

```powershell
azmqos qec-decoder-demo --output-dir outputs\qec_decoder_demo
```

Production decoder workflow:

```powershell
azmqos production-qec-decode --config outputs\production_project\azmqos_production.json --code repetition3 --max-components 2 --shots 64
```

## Main outputs

- `syndrome_samples.csv`
- `decoder_results.csv`
- `decoded_estimates.csv`
- `decoded_estimates.json`
- `M_decoded_logical_estimates.csv`
- `V_decoded_logical_estimates.csv`
- `decoded_estimates.png`
- `qec_decoder_report.md`
- `production_qec_decoder_manifest.json`
