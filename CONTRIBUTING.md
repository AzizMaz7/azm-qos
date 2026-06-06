# Contributing to AZM-QOS

Thank you for your interest in AZM-QOS.

At the current stage, this repository is intended primarily for private PhD research development and advisor-reviewed release preparation.

## Local setup

```powershell
python -m pip install -e .
```

## Run public-release validation

```powershell
azmqos public-release-info --output-dir outputs\public_release_info
azmqos public-release-validate --output-dir outputs\public_release_validate
```

## Run tests

```powershell
python tests\test_v5_0_public_release.py
```

## Do not commit

- IBM tokens or API keys.
- `job_ids.json`.
- Real private backend calibration files.
- Generated `outputs/`.
- Runtime cache folders.
- Unpublished results that should remain private.

## Code style

Prefer small, explicit modules with clear dataclasses, deterministic local fallback behavior, and conservative labels for synthetic/scaffold results.
