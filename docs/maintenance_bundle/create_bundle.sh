#!/usr/bin/env sh
set -eu

export LC_ALL=C
export LANG=C

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
OUT_DIR="$ROOT/docs/maintenance_bundle"
ARCHIVE="$OUT_DIR/hermes-agent-ha-addon-docs.tar.gz"
MANIFEST="$OUT_DIR/MANIFEST.txt"
SUMS="$OUT_DIR/SHA256SUMS"

cd "$ROOT"

cat >"$MANIFEST" <<'EOF'
README.md
INSTALL.md
repository.yaml
.github/workflows/lint.yml
docs/AI_MAINTENANCE.md
docs/OPERATIONS_ARCHIVE.md
docs/UPGRADE_LOG.md
docs/ARCHITECTURE.md
docs/STORAGE.md
docs/maintenance_bundle/README.md
docs/maintenance_bundle/create_bundle.sh
hermes_agent/README.md
hermes_agent/DOCS.md
hermes_agent/CHANGELOG.md
hermes_agent/config.yaml
hermes_agent/Dockerfile
hermes_agent/run.sh
hermes_agent/hermes_ui/version.json
hermes_agent/patches/README.md
hermes_agent/patches/ha_ws_url.py
hermes_agent/scripts/configure.py
hermes_agent/scripts/install-ttyd.sh
hermes_agent/scripts/bake-version.py
hermes_agent/scripts/_fetch.py
hermes_agent/translations/en.yaml
hermes_agent/translations/zh.yaml
EOF

tar -czf "$ARCHIVE" -T "$MANIFEST"

archive_name="$(basename "$ARCHIVE")"
if command -v shasum >/dev/null 2>&1; then
  (cd "$OUT_DIR" && shasum -a 256 "$archive_name") >"$SUMS"
elif command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUT_DIR" && sha256sum "$archive_name") >"$SUMS"
else
  printf 'No sha256 tool found; archive generated without checksum.\n' >&2
  : >"$SUMS"
fi

printf 'Generated %s\n' "$ARCHIVE"
