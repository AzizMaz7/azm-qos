# Public Release Checklist

Use this only after advisor approval and paper/preprint strategy are clear.

## Before public release

- [ ] Advisor approves public repository.
- [ ] No private credentials.
- [ ] No private job IDs.
- [ ] No generated outputs.
- [ ] No confidential/unpublished data.
- [ ] README is accurate.
- [ ] LICENSE is present.
- [ ] CITATION.cff is updated.
- [ ] CHANGELOG.md is updated.
- [ ] Tests pass.

## Release steps

```powershell
git tag -a v5.0.0 -m "AZM-QOS v5.0.0 stable public research release"
git push origin v5.0.0
```

Then create a GitHub Release from tag `v5.0.0`.

## Zenodo

After making GitHub public and creating a GitHub Release, archive the release on Zenodo and update:

- `CITATION.cff`
- `.zenodo.json`
- `README.md`
