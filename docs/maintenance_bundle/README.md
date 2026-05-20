# Maintenance Documentation Bundle

This directory contains a portable documentation bundle for future AI or human
maintainers.

## Contents

- `hermes-agent-ha-addon-docs.tar.gz` — generated archive containing the public
  maintenance docs and critical add-on files.
- `MANIFEST.txt` — exact files included in the archive.
- `SHA256SUMS` — checksum for the generated archive.
- `create_bundle.sh` — regeneration script.

## Regenerate

From the repository root:

```bash
./docs/maintenance_bundle/create_bundle.sh
```

The bundle intentionally excludes `.ops/`, local tokens, build caches, and Git
metadata. It is safe to commit.

## First File To Read After Extracting

```text
docs/AI_MAINTENANCE.md
```
