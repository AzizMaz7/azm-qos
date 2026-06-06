# AZM-QOS v4.2 Decoder Workflow Guide

The v4.2 decoder workflow does:

1. Run QEC logical estimates.
2. Simulate syndrome samples.
3. Decode each syndrome using a repetition-code lookup table.
4. Compare raw, postselected, and corrected logical estimates.
5. Estimate uncertainty from corrected logical samples.
6. Export decoded M/V tables and dashboard artifacts.

This is a scaffold. Final QEC studies should use real syndrome measurements, a validated decoder, and code-specific logical correction rules.
