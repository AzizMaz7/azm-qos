# AZM-QOS v4.1 QEC Workflow Guide

The v4.1 workflow does:

1. Load selected END/VQS Pauli components.
2. Select a stabilizer-code scaffold.
3. Map physical Pauli terms into logical Pauli terms.
4. Generate syndrome-measurement scaffolds.
5. Estimate logical and syndrome-accepted physical observables.
6. Export M/V logical estimate tables.
7. Attach QEC estimates to the run database and dashboard.

This release is intentionally an initial scaffold. Real QEC production requires a decoder, code-specific logical circuits, fault-tolerant syndrome extraction, and hardware-calibrated noise models.
