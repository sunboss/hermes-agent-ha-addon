# Release Process

Use this process for every add-on release.

## Version Policy

Add-on version format:

```text
YYYY.M.D.N
```

Examples:

- `2026.5.20.0`
- `2026.5.20.1`

Use the final component for multiple releases on the same date.

## Upstream Image Policy

Prefer explicit upstream calendar tags:

```text
nousresearch/hermes-agent:vYYYY.M.D
```

Avoid for stable add-on releases:

- `latest`
- `main`
- moving `sha-*` tags unless the user explicitly asks for a risky test build.

Before bumping, confirm Docker Hub exposes the calendar tag.

## Files To Update

For every add-on release:

- `hermes_agent/Dockerfile`
- `hermes_agent/config.yaml`
- `hermes_agent/hermes_ui/version.json`
- `README.md`
- `hermes_agent/CHANGELOG.md`
- `docs/UPGRADE_LOG.md`
- `docs/OPERATIONS_ARCHIVE.md` when runtime behavior was verified.
- `docs/AI_MAINTENANCE.md` if invariants or known-good versions change.

After documentation changes:

- Run `./docs/maintenance_bundle/create_bundle.sh`.
- Commit the updated archive, manifest, and checksum.

## Local Checks

```bash
bash -n hermes_agent/run.sh docs/maintenance_bundle/create_bundle.sh
PYTHONPYCACHEPREFIX="$PWD/.pycache-check" python3 -m py_compile \
  hermes_agent/hermes_ui/server.py \
  hermes_agent/hermes_ui/auth_bridge.py \
  hermes_agent/hermes_ui/provider_shim.py \
  hermes_agent/scripts/_fetch.py \
  hermes_agent/scripts/bake-version.py \
  hermes_agent/scripts/configure.py \
  hermes_agent/patches/ha_ws_url.py
python3 -c "import glob, yaml; [yaml.safe_load(open(f, encoding='utf-8')) for f in glob.glob('hermes_agent/**/*.yaml', recursive=True) + glob.glob('hermes_agent/**/*.yml', recursive=True)]; print('yaml ok')"
git diff --check
```

Check that secrets are not staged:

```bash
git status --short --ignored .ops
git diff --cached | rg 'Personal access token|OPENAI_API_KEY=|OPENROUTER_API_KEY=|API key:'
```

The second command should return no matches.

## Commit And Push

```bash
git add <changed-files>
git commit -m "<clear release or documentation message>"
GIT_ASKPASS=.ops/git-askpass.secret.sh GIT_TERMINAL_PROMPT=0 \
  git -c http.version=HTTP/1.1 push origin main
```

Never put the token in the remote URL or commit message.

## GitHub Actions

After push, check:

```text
https://github.com/sunboss/hermes-agent-ha-addon/actions
```

The current workflow performs:

- Bash syntax check.
- Python syntax check.
- YAML syntax check.
- Dockerfile lint.

It does not perform a real HAOS image build.

## HAOS Verification

After push:

1. `ha store reload`
2. `ha supervisor reload`
3. Update or rebuild the add-on.
4. Start the add-on.
5. Verify healthy logs from `docs/HAOS_RUNBOOK.md`.
6. Record the observed result in `docs/OPERATIONS_ARCHIVE.md`.

## Rollback

Rollback is a normal release:

1. Revert the upstream image / wrapper changes.
2. Bump add-on version forward.
3. Explain the rollback in `CHANGELOG.md` and `UPGRADE_LOG.md`.
4. Push to `main`.
5. Rebuild in HAOS.

Do not force-push public release history unless the user explicitly asks and
understands the risk.
