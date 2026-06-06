# AZM-QOS v2.0 Reproducible Research Platform

v2.0 adds the research-output layer.

## New package

```text
azmqos_research
```

## Main features

- Experiment manifests
- CSV tables
- Automatic figures
- Markdown reports
- LaTeX reports
- Reproducibility bundles
- CLI entry point

## Main command

```bash
azmqos run --output-dir outputs/my_run --shots 1024 --rounds 5 --trials 100
```

## Important limitation

v2.0 can generate manuscript-style reports, but the scientific validity depends on whether the END/VQS registry contains real derived terms or proxy terms.
