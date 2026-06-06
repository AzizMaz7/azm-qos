# AZM-QOS v2.1 Real END/VQS Terms Workflow

v2.1 adds the workflow for using real derived END/VQS Pauli decompositions.

## Main command

```bash
azmqos real-terms \
  --component-registry templates/endvqs_real_terms_template.json \
  --output-dir outputs/real_terms_run
```

## What it does

1. Loads your registry.
2. Validates M and V entries.
3. Runs END/VQS workloads.
4. Assembles M and V.
5. Runs detector-error-model and matching-decoder diagnostics.
6. Exports CSV, figures, reports, manifest, and reproducibility bundle.

The template file must be edited with your actual derived terms before the numerical results become meaningful.
