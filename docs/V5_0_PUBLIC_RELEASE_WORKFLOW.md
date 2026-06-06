# v5.0 Public Release Workflow

1. Install with `python -m pip install -e .`.
2. Initialize production config with `azmqos production-init`.
3. Export public release metadata with `azmqos public-release-info`.
4. Validate the public release with `azmqos public-release-validate`.
5. Use v4.9 `production-release-run` for the full final package workflow.
