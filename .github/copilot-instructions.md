<!-- Copilot / AI agent guidance for `first-setup` -->

This file gives repository-specific, actionable guidance for AI coding agents working on this project.

1. Project summary
- Purpose: a GNOME/GTK-based "first setup" wizard for SNOW Linux that configures hostname, user, locale, installs flatpaks, etc.
- Language & build: Python app bundled with GNOME resources; built with Meson and packaged as a Debian package (`debian/`).

2. Key entry points & locations
- Runtime entry: `snow_first_setup/main.py` — it loads the compiled GResource (`snow-first-setup.gresource`) and instantiates `FirstSetupApplication`.
- Application logic: `snow_first_setup/application.py` and `snow_first_setup/core/` contain business logic and backend helpers.
- Scripts that run on the target image: `snow_first_setup/scripts/` (installed to `/usr/share/org.frostyard.FirstSetup/snow_first_setup/scripts/`).
- UI/resource files: `snow_first_setup/snow-first-setup.gresource.xml` and assets in `snow_first_setup/assets/`.
- Packaging and metadata: `debian/` (control, install, rules) and top-level `meson.build` files.

3. Developer workflows (commands you should prefer)
- Run the app locally (dry-run): `python3 test.py -d` (safe — does not modify system).
- Change language for testing: `LANGUAGE=de python3 test.py -d`.
- Install native build deps (Debian-based): `sudo apt-get update && sudo apt-get build-dep .`.
- Meson build and compile: `meson setup build` then `meson compile -C build`.
- Build Debian package: `dpkg-buildpackage` (artifacts placed in parent directory).
- Install built package: `sudo apt-get install ./snow-first-setup*.deb` or `meson install -C build`.
- Update translation POT: `meson compile -C build snow-first-setup-pot`.

4. Project-specific patterns & conventions
- Dry-run safety: `test.py` supports `-d`/`--dry-run`. Use it for iterative changes to avoid system modifications.
- Meson-first resources: gresource is built into `snow-first-setup.gresource`. When changing UI XML or assets, ensure meson re-bundles the resource and tests with `meson compile -C build`.
- Packaging alignment: runtime dependencies are declared in `debian/control`. If you add imports, update that file so Debian builds/installers remain correct.
- System scripts vs. app code: scripts used on the image are under `scripts/` (these are executed on target systems — keep them idempotent and avoid local-only dev helpers there).
- Translation flow: source strings are in `po/` and `snow_first_setup/*.py`; updating strings requires regenerating the POT and possibly syncing PO files.

5. What to check before changes
- Entrypoints: after code edits, search `snow_first_setup/main.py` to confirm registered resources and `FirstSetupApplication` usage are unchanged.
- Meson integration: open `meson.build` entries in the top-level and `snow_first_setup/meson.build` to ensure new files are included in the `gresource` target.
- Debian package impact: modify `debian/control` when adding runtime dependencies; modify `debian/*.install` when changing installed paths.

6. Examples (copyable)
- Run dry-run: `python3 test.py -d`
- Full build: `meson setup build && meson compile -C build`
- Update translations: `meson compile -C build snow-first-setup-pot`
- Build package: `dpkg-buildpackage`

7. Releases and CI workflows
- A `vX.Y.Z` tag (from `just bump`) runs `.github/workflows/release.yml`: build, attest, GitHub release, then a `publish-deb` dispatch to `frostyard/apt-publisher`, which publishes the `.deb` to the Debian repository and triggers the snosi rebuild. Never add a direct upload, signing step or snosi dispatch here; apt-publisher is the single Debian writer (frostyard/core ADR-0055/0056).
- Pin every action to a full commit SHA with a `# vX.Y.Z` comment, keep `permissions:` minimal, and pass `${{ }}` values to `run:` through `env:`. `just test` (`tests/test_workflows.py`) enforces this; update it with any workflow change.

8. When editing files that affect the image
- If you change `snow_first_setup/scripts/*`, remember these are the scripts shipped to images. Keep them small, documented, and idempotent.
- If you change session files or desktop entries, update `data/` files (e.g., `org.frostyard.FirstSetup.desktop.in`) and the corresponding `meson.build` install stanza.

9. Quick pointers for AI code edits
- Prefer minimal, targeted changes: update `meson.build` or `debian/control` only when necessary.
- When adding CLI flags or behavior, keep `test.py` parity (dry-run support) and update README examples.
- Use `gettext` patterns already present (`gettext.install('snow-first-setup', localedir)`) — add new translatable strings using `_('text')`.

10. Useful files to inspect when diagnosing issues
- `README.md` — build/run workflows and commands.
- `snow_first_setup/main.py` — app boot sequence.
- `snow_first_setup/application.py` and `snow_first_setup/core/` — logic and flow.
- `meson.build` (top-level and `snow_first_setup/`) — bundling/resources.
- `debian/control` and `debian/*.install` — packaging/dependencies.

If anything in these instructions is unclear or you want more detail in a particular area (packaging, translations, meson targets, or runtime scripts), tell me which area and I'll expand it.
