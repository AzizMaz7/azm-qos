# AZM-QOS v2.2 Shot-Scaling Guide

The shot-scaling workflow evaluates one END/VQS workload across shot counts:

```text
shots = 2^n
```

and exports:

```text
shot_scaling.csv
shot_scaling_loglog.png
```

The plot uses:

```text
x = log2(shots)
y = log2(abs(error))
```

where the exact local statevector backend is used as the reference.
