# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Koan ("kickstart-over-a-network") is the client-side companion to
[Cobbler](https://github.com/cobbler/cobbler). It runs on a target machine and talks to a Cobbler
server to either provision new virtualized guests (Xen, KVM/qemu, VMware, OpenVZ) or re-provision
(re-kickstart) an existing physical/virtual system. It ships two console scripts: `koan` (the big
`Koan` CLI in `app.py`) and `cobbler-register` (the small `Register` CLI in `register.py`).

## Commands

Development install and dependency groups are declared in `setup.cfg` (`[options.extras_require]`:
`build`, `lint`, `test`, `docs`).

```bash
# Install with test + lint extras
pip install -e .[lint,test]

# Run the full test suite with coverage (this is what CI runs)
pytest --cov=./koan

# Run a single test file / test
pytest tests/test_utils.py
pytest tests/test_utils.py::test_os_release

# Lint (pyflakes only checks top-level *.py and koan/*.py, not tests/)
pyflakes *.py koan/*.py

# Format (black is also enforced via pre-commit and CI)
black --safe .
```

`make qa` runs pyflakes + black if available locally. `make doc` builds the Sphinx docs in
`docs/`. `make release` (clean → qa → authors → sdist → bdist → doc) is the full local release
build; `make rpms` / `make debs` build native packages and depend on `setuptools_scm`-derived
versioning being consistent — see the comments above `pin-spec-version` and `debs` in `Makefile`
if touching packaging.

Versioning is entirely derived from git tags via `setuptools_scm` (`pyproject.toml`,
`koan/_version.py` is generated — never hand-edit it). There is no manual version bump.

## Commit messages / releases

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/) — enforced by
the `commitlint` CI job (see `CONTRIBUTING.md` and `commitlint.config.js`). Merges to `main` are
released automatically by `semantic-release`: the version, tag, GitHub release, and
`CHANGELOG.md` are all generated from commit messages, so `feat:`/`fix:`/`!`/`BREAKING CHANGE:`
prefixes directly control the next release. Malformed commit messages will fail CI and won't
release correctly, so this matters more here than in most repos.

The `package.json` / `node_modules` tooling in this repo (`semantic-release`, `commitlint`) is
release automation only — koan itself has no JavaScript runtime code.

## License headers

Source files use SPDX headers, not the older GPL docstring blocks (converted in a recent PR):

```python
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright <year> <holder>
```

Add these to any new source file; match the existing pattern (module docstring first, then the
SPDX comment block, then imports).

## Architecture

Everything lives in the flat `koan/` package (no subpackages):

- **`app.py`** — the real core of the program: the `Koan` class implements the entire `koan` CLI
  (~2100 lines). `main()` parses options with `optparse` and drives one `Koan` instance through a
  single top-level action (`--virt`, `--replace-self`, `--update-files`, `--update-config`,
  `--list`, etc. — see `Koan.run()`). Key method groups:
  - `net_install()` / `get_distro_files()` / `calc_kernel_args()` — fetch profile/system data
    from the Cobbler server and compute kernel/initrd/kernel-options for network installs and
    `--replace-self` (kexec) reinstalls.
  - `virt_net_install()` / `load_virt_modules()` / `virt_choose()` — dispatch to the
    per-hypervisor `*create.py` module based on `virt_type`.
  - The many `calc_virt_*()` methods (`calc_virt_ram`, `calc_virt_disk`-adjacent
    `calc_virt_filesize*`, `calc_virt_mac`, `calc_virt_uuid`, `calc_virt_path*`, ...) resolve
    per-VM settings from Cobbler profile/system data plus command-line overrides plus defaults —
    this layered override pattern (CLI arg > profile data > hardcoded default) is used
    throughout and is the main thing to preserve when touching option handling.
  - `update_files()` / `update_config()` — pull config-management templates/packages/repos from
    Cobbler for an already-installed system and hand off to `configurator.KoanConfigure`.
- **`configurator.py`** — `KoanConfigure`: applies repo/package/file configuration pushed down
  from Cobbler's config-management data to the local system (currently only implements YUM repo
  configuration; `yum` import is optional/best-effort).
- **`virtinstall.py`** — builds a `virt-install`/libvirt command line (disk/NIC sanitization,
  `build_commandline()`) for KVM/qemu and Xen-via-libvirt guests.
- **`{xen,qcreate,openvz,vmw,image}create.py`** — one module per hypervisor/guest backend, each
  exposing a `start_install(*args, **kwargs)` entry point that `app.py` calls into via
  `virt_choose()`/`load_virt_modules()`. `vmwcreate.py` additionally has helpers to build VMX
  files and register/start guests through VMware. When adding a new virt backend, follow this
  same `start_install(**kwargs)` contract so it plugs into `app.py` unchanged.
- **`utils.py`** — shared grab-bag: XML-RPC connection to the Cobbler server
  (`connect_to_server`), network/OS introspection (`get_network_info`, `os_release`,
  `is_uefi_system`), subprocess helpers, and misc file/MAC/UUID utilities used across the other
  modules.
- **`register.py`** — a second, much smaller CLI (`Register` class) for the `cobbler-register`
  command, which just registers the current system with a Cobbler server (distinct from the main
  provisioning flow in `app.py`).
- **`cexceptions.py`** — exception hierarchy. `KoanException`/`InfoException` set a
  `from_koan` marker so `main()` can print a clean one-line message instead of a traceback for
  expected/user-facing errors; anything else prints a full traceback.

## Tests

`tests/` currently only covers `utils.py` (`test_utils.py`), using `pytest-mock` to stub
`os.path`/`distro`/subprocess calls rather than touching a real system or network — follow that
mocking style for new tests, since most of `koan`'s code paths require root, libvirt, or a live
Cobbler server to exercise for real. `tests/conftest.py` provides a `does_not_raise()` context
manager for parametrized tests that assert "no exception" as one case among several
`pytest.raises(...)` cases. `tests/virtinstall.py` is not a `test_*.py` file, so pytest won't
collect it as a test module.