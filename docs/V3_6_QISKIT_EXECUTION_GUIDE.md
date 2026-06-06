# AZM-QOS v3.6 Qiskit Execution Guide

Backend options:

- `auto`: try Aer, then BasicSimulator, then fallback
- `aer`: require qiskit-aer
- `basic`: require Qiskit BasicSimulator
- `fallback`: dependency-free deterministic grouped-count execution
- `hardware_dry_run`: create dry-run job IDs and circuit metadata; no IBM submission

The default state-preparation hook is a placeholder Ry preparation. Replace it with the actual END/VQS state-preparation circuit when moving from scaffold to scientific production.
