# Security Policy

## Private data

Do not commit:

- IBM Quantum tokens.
- API keys.
- `.env` files.
- `job_ids.json`.
- Private backend calibration files.
- Runtime caches.
- Raw unpublished hardware results unless approved for release.

## Reporting issues

For private research-stage development, report issues directly to the repository owner.

## Synthetic vs real data

Synthetic fallback records are software-validation records, not real hardware evidence. Real hardware analysis should be clearly labeled and should include provenance for job IDs, counts, and calibration metadata.
