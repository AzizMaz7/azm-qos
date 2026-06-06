# AZM-QOS v2.6 Uncertainty Interpretation

The v2.6 uncertainty layer estimates finite-shot statistical uncertainty.

It does not automatically include:

- calibration drift
- systematic readout bias
- gate-model mismatch
- transpiler-induced circuit differences
- backend queue-time drift
- error mitigation model bias

For publication, report both statistical intervals and known systematic limitations.
