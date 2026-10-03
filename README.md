<div align="center">
    <img src="data/icons/hicolor/scalable/apps/org.frostyard.FirstSetup.svg">
    <h1>SNOW First Setup</h1>
    <p>First-login personal setup wizard for SNOW Linux. It runs once per
    user on their first login and handles light per-user preferences:
    light/dark style, optional flatpak applications, and small per-user
    conveniences.</p>
</div>

## Scope

This tool only does **first-login, per-user** setup. Installation and all
system-level configuration (disk install, hostname, locale, keyboard,
timezone, user creation, system extensions) are handled by
[firn](https://github.com/frostyard/firn), the snosi installer — the old
installer and first-boot configure modes that used to live here have been
removed.

What remains:

- Welcome page with accessibility settings shortcut
- Internet connectivity check
- Light/dark style preference
- Optional per-user flatpak applications (from `snow_first_setup/apps.json`,
  installed with `flatpak --user` from Flathub)
- Small per-user conveniences (e.g. Homebrew shell setup in `~/.bashrc`)

## How it is launched

The package installs a system-wide XDG autostart entry
(`/etc/xdg/autostart/org.frostyard.FirstSetup.autostart.desktop`) that runs
`snow-first-setup --autostart` on every graphical login. The app exits
immediately when the per-user completion marker
(`~/.config/snow-first-setup.done`, written by the `complete-setup` script
when the wizard finishes) exists, or when running in a live session.

## `core.json` contract

`snow_first_setup/core.json` is installed to
`/usr/share/org.frostyard.FirstSetup/snow_first_setup/core.json` and is a
cross-repo contract: it defines the core system flatpak set that
[firn](https://github.com/frostyard/firn) installs at install time
(`core_flatpaks`) and that `snosi-firstboot` provisions on first boot. It is
not read by this wizard itself, but it must keep shipping at exactly that
path.

## Run without building for testing

> [!IMPORTANT]
> You need to install all build and run dependencies first

```bash
python3 test.py -d
```

The `-d` option is the dry-run mode; without it, first-setup will make
changes to your user account.

### Test translations

You can change the used language like this:

```bash
LANGUAGE=de python3 test.py -d
```

## Build

### Installing build dependencies

```bash
sudo apt-get update
sudo apt-get build-dep .
```

If you want to install the build dependencies manually, have a look in
[debian/control](debian/control).

### Building

> [!WARNING]
> dpkg-buildpackage places its output files (like the .deb file) into the
> parent folder.

```bash
dpkg-buildpackage
```

or manually with meson:

```bash
meson setup build
meson compile -C build
```

Here you can change the install folder (default is /usr/local), for example:

```bash
meson setup --prefix="$(pwd)/install" build
```

## Installing

```bash
sudo apt-get install ./snow-first-setup*.deb
```

or manually with meson:

```bash
meson install -C build
```

## Run

```bash
snow-first-setup
```

### Flags

- `--dry-run (-d)`: Don't make any changes to the system.
- `--autostart (-a)`: Used by the autostart entry; exits immediately if this
  user already completed first setup or in a live session.

## Update translation file

To update the .pot file with newly added translation strings, run:

```bash
meson compile -C build snow-first-setup-pot
```

## Adjust for a custom image

The scripts which are used to apply the user's choices can be found in
`/usr/share/org.frostyard.FirstSetup/snow_first_setup/scripts/`. Overwrite
them to your needs in your image.

## Releasing

`just bump` writes the next version into `debian/changelog`, commits it,
and pushes the matching `vX.Y.Z` tag. The tag runs
[`release.yml`](.github/workflows/release.yml), which:

1. checks that the tag matches the `debian/changelog` version, then builds
   the package in `debian:trixie`;
2. attests `snow-first-setup_<version>_all.deb` and `checksums.txt` with
   GitHub build provenance;
3. creates the GitHub release with those two files;
4. asks `frostyard/apt-publisher` (a private repository) to publish the
   release: a `publish-deb` dispatch, authenticated by the
   `APT_PUBLISH_TOKEN` secret.

apt-publisher is the only writer of the Frostyard Debian repository
([core ADR-0055](https://github.com/frostyard/core/blob/main/docs/adr/0055-publish-debian-packages-through-the-apt-publisher.md)).
It verifies the attestation against the tag, publishes the package to
`trixie` at `https://repository.frostyard.org/debian/`, and then asks
[snosi](https://github.com/frostyard/snosi) to rebuild its images
([core ADR-0056](https://github.com/frostyard/core/blob/main/docs/adr/0056-rebuild-images-after-apt-publication.md)).
This repository does not sign or upload packages itself.

If the publication request fails, the release already exists: fix the
cause, then use "Re-run failed jobs" on the release run.

The release must carry exactly one `.deb`, named
`snow-first-setup_<version>_all.deb`: apt-publisher publishes every `.deb`
asset under its file name.

`just test` runs the workflow contract tests in `tests/` (they need
`python3-yaml`). They pin this release flow and require every action to be
pinned to a commit SHA.

## Provenance

Forked from [Vanilla OS first-setup](https://github.com/Vanilla-OS/first-setup).
