# AZM-QOS v3.9 Mitigation Workflow Guide

The v3.9 workflow applies:

1. Readout mitigation to plus/minus shifted observable values.
2. ZNE-style extrapolation of derivative estimates.
3. Combined derivative estimate from readout-mitigated and ZNE values.
4. Propagated uncertainty using raw shot uncertainty and mitigation spread.
5. Shot-allocation scaffold based on derivative uncertainties.

The default calibration and noise models are scaffolds. Replace them with actual backend calibration data for hardware studies.
