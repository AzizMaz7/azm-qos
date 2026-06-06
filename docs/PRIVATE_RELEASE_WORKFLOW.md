# Private GitHub Release Workflow

This repository is prepared for a **private GitHub repository first**, with public release later after advisor approval and paper/preprint strategy is clear.

## Recommended order

```text
1. Private GitHub repository now
2. Advisor review
3. Paper/preprint preparation
4. Make GitHub public
5. Create GitHub Release v5.0.0
6. Connect to Zenodo and mint DOI
7. Update citation metadata
```

## Do not publish yet

Before public release, check:

- No IBM tokens.
- No private `job_ids.json`.
- No private `backend_calibration.json`.
- No generated `outputs/`.
- No unpublished private hardware results.
- No paper figures that should remain private.
- Advisor approves release.

## Private GitHub setup

```powershell
git init
git add .
git commit -m "Prepare AZM-QOS v5.0.0 private release candidate"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AZM-QOS.git
git push -u origin main
```

Keep the repository private until ready.
