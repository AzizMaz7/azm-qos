# AZM-QOS v3.8 Derivative Workflow Guide

The v3.8 workflow evaluates:

```text
parameter-shift derivative = 1/2 [f(theta + s) - f(theta - s)]
```

and compares it to a central finite difference:

```text
finite difference = [f(theta + h) - f(theta - h)] / (2h)
```

The default implementation uses the current END/VQS state-preparation scaffold and fallback-safe execution. Replace the scaffold ansatz with exact END/VQS unitaries before using derivative values as final scientific results.
