# AZM-QOS v4.3 FT-QEC Workflow Guide

The v4.3 workflow does:

1. Build repeated syndrome-extraction circuit specs.
2. Define a circuit-level noise model scaffold.
3. Run v4.2 decoder estimates as a base layer.
4. Simulate repeated syndrome rounds.
5. Estimate logical failure rates.
6. Compare raw, decoded, and FT-corrected estimates.
7. Export QEC-aware M/V tables and dashboards.

This is still a scaffold. For final work, replace deterministic round simulation with real syndrome circuits, backend noise models, and validated decoders.
