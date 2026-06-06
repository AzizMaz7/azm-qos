# AZM-QOS v4.4 Hardware Workflow Guide

The v4.4 workflow does:

1. Build repeated syndrome-extraction specs.
2. Convert specs into Qiskit circuits when Qiskit is installed.
3. Transpile locally using a backend-target scaffold.
4. Compute resource summaries.
5. Check ISA-style constraints.
6. Generate dry-run job manifests.
7. Recommend a compact noise-aware layout.
8. Export hardware dry-run reports and dashboard artifacts.

No hardware job is submitted.
