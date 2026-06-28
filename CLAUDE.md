# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pwncloudos-sync` performs in-place upgrades of the ~44 security tools bundled with
[PwnCloudOS](https://pwnedlabs.io/pwncloudos) so users don't have to re-download OS images. It is a
Python 3.10+ CLI that reads a tool manifest, detects installed-vs-latest versions, and updates each
tool with the method appropriate to how it was installed (git, pipx, binary, docker, apt, custom
script, or file replacement) — always with a backup and automatic rollback on failure.

## Running

```bash
pip3 install -r requirements.txt --break-system-packages   # first time only

python3 -m src.main              # default: check all tools, show table, offer to update
python3 -m src.main --list       # list tools + versions (no network, no changes)
python3 -m src.main --check      # check for updates only
python3 -m src.main --all -y     # update everything, skip confirmation
python3 -m src.main --category aws          # scope to a category
python3 -m src.main --tool cloudfox --tool prowler   # scope to named tools
python3 -m src.main --dry-run -vv           # show plan, debug logging, no changes
./pwncloudos-sync [args]         # bash wrapper (enforces Python >= 3.10, then runs src.main)
```

### Install mode

`./pwncloudos-setup` (bash bootstrapper at repo root) is the one-shot provisioner for a fresh Kali / Ubuntu / Debian host. Execution order:

1. Detect distro and arch (Kali vs Ubuntu/Debian; amd64 vs arm64).
2. Install system prerequisites: apt base packages, `pwsh` (via Kali repo on Kali, Microsoft apt repo elsewhere), Docker CE, `uv`, John build deps.
3. Create the `/opt/<category>` directory tree.
4. Install this repo's Python dependencies (via `uv` or `pip3`).
5. Call `python3 -m src.main install` to clone/configure every manifest tool.

```bash
./pwncloudos-setup              # full provision, interactive
./pwncloudos-setup -y           # skip all prompts
./pwncloudos-setup --dry-run    # show plan, make no changes
./pwncloudos-setup --no-prereqs # skip system package installs
./pwncloudos-setup --no-configs # skip launchers / profiles / icons
./pwncloudos-setup --no-desktop # skip XFCE menu entries
```

`python3 -m src.main install` (Python layer) uses install-aware updater routing:
`get_updater_for_tool(for_install=True)` selects the correct `BaseUpdater` subclass and calls
`perform_install()` on each tool. After tools are cloned, the configs/menu phase
(`src/installer/configs.py`, `src/installer/menu.py`) installs a **bundled** PowerShell profile
(`src/installer/data/`, ported from linux-setup — no network fetch), then fetches launchers, icons,
and XFCE `.desktop` entries from the upstream `pwnedlabs/pwncloudos` repo.

**Install invariants** (distinct from sync invariants):

- `pwsh` + its PowerShell profile are installed. The profile is **bundled** in this repo
  (`src/installer/data/`); its light/dark theme is chosen from a terminal probe done by the
  bootstrapper and passed to the Python layer via `PWNCLOUDOS_TERMINAL_BG`. **`.zshrc` is never
  modified.**
- XFCE desktop menu entries are created only when a graphical (XFCE) session is detected; they use
  user-level, vendor-prefixed IDs and do not overwrite the existing Kali menu.
- All file writes are confined to `/opt`, `/usr/share/pwncloudos`, `~/.config`, `~/.local/share`, and
  `~/.profile` (the bootstrapper's PATH entries + `POWERSHELL_TELEMETRY_OPTOUT`; never `.zshrc`).
- On a real PwnCloudOS VM (all tools already present), install is effectively a no-op; `pwncloudos-sync`
  handles updates thereafter.

There is **no automated test suite**. Verify changes against a live PwnCloudOS VM, or locally with
`--list` / `--check` / `--dry-run` (these are safe and most paths run without network or sudo).
`--list` and most version detection work without `/opt/` tools present (they just report missing).

## Architecture

Manifest-driven Strategy pattern. The flow, all orchestrated in `src/main.py`:

1. **`manifests/tools.yaml`** is the source of truth — every updatable tool, its `category`,
   `install_method`, `path`, `github_repo`, `arch_support`, etc. `src/tools/registry.py` loads it
   into `Tool` dataclasses (falling back to filesystem discovery only if no manifest is found).
2. **`get_updater_for_tool()`** (`registry.py`) maps each tool's `install_method` to one updater
   class in `src/updaters/`, all subclasses of `BaseUpdater` (`updaters/base.py`):
   `git`/`git_python`, `pipx`, `binary`, `apt`, `docker`, `custom`, `file_replacement`. Each
   implements `get_current_version` / `get_latest_version` / `needs_update` / `perform_update` /
   `verify_update`.
3. **Per-tool update cycle** (`update_tool()` in `main.py`): skip if arch unsupported →
   `validate_update_target()` (safeguards) → `needs_update()` check → backup via `RollbackEngine` →
   `perform_update()` → `verify_update()`. On any failure or failed verification, the rollback engine
   restores. Failed tools are retried once after the first pass.
4. **`src/core/`** holds cross-cutting concerns: `safeguards.py` (path allow/deny), `rollback.py`
   (per-method backup + restore), `arch.py` (amd64/arm64 detection), `connectivity.py`,
   `privileges.py` (sudo), `state.py` (version cache in `~/.cache/pwncloudos-sync/state`).

Config precedence (`src/config.py`): dataclass defaults < `~/.config/pwncloudos-sync/config.yaml` <
CLI args. Backups live in `~/.cache/pwncloudos-sync/backups`.

## Critical Invariants

These exist because the updater runs against a curated OS image and must never break a working tool
or destroy PwnCloudOS's customizations:

- **Never modify launcher files.** PwnCloudOS injects `*Launcher*` / `*_launcher*` scripts and
  untracked `.ps1` files *inside* tool repos. `GitUpdater._backup_launcher_files` /
  `_restore_launcher_files` read them into memory before any git mutation and restore them in a
  `finally` block (even on failure). **Never use `git clean`** anywhere — it would delete them.
- **Path gating before every write.** `safeguards.validate_update_target()` must be called before any
  file modification. It rejects anything matching `PROTECTED_PATHS` (launchers, `.desktop`,
  `docs/configs/`, shell rc files, `*.conf`) and anything outside `ALLOWED_UPDATE_PATHS` (the
  `/opt/*_tools/` dirs, `~/.local/bin`, pipx venvs, etc.). Err toward protection.
- **`/opt/` is root-owned but the tool runs as a user.** Updaters detect this (`_needs_sudo`) and
  prepend `sudo` for write ops, and auto-add repos to git `safe.directory`. Preserve this when
  touching any updater or the rollback engine.
- **Custom scripts are sandboxed by name.** `CustomUpdater` resolves `custom_handler` via
  `os.path.basename` against `scripts/` only — no path traversal. New custom updaters add a script to
  `scripts/` and reference it by bare filename in the manifest (it receives `ARCH`, `TOOL_NAME`,
  `TOOL_PATH` env vars).

## Adding or Changing Tools

Most tool changes are manifest-only edits to `manifests/tools.yaml` — no code change needed if an
existing `install_method` fits. Adding a *new* install method means a new `BaseUpdater` subclass,
exporting it in `src/updaters/__init__.py`, and wiring it into `get_updater_for_tool()`.

## Gotchas

- `--parallel` / `--workers` flags are parsed and stored in config but the update loop in `main.py`
  is still sequential — they are currently no-ops.
- PowerShell module versions (`ps_module_manifest`) are read via `pwsh -Command Import-PowerShellDataFile`;
  detection silently falls back to a git hash if `pwsh` is absent.
- Exit codes are meaningful: `0` all ok, `1` partial failure, `2` all failed, `3` arch detection,
  `4` no connectivity, `5` no sudo.

## Note on `/opt/linux-setup`

This is added as a secondary working directory but is an unrelated project (a Debian/Kali setup
shell script). It has its own `CLAUDE.md` — do not conflate the two repos.
