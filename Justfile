set dotenv-load := true


default:
    @just --list --unsorted

setup:
    @echo "Setting up development environment..."
    distrobox assemble create
    distrobox enter first-setup

enter:
    @distrobox enter first-setup

build:
    @echo "Building the project..."
    meson setup build
    meson compile -C build

build-deb:
    @echo "Building Debian package..."
    dpkg-buildpackage -us -uc -b

clean:
    @echo "Cleaning build artifacts..."
    dpkg-buildpackage -Tclean

changelog:
    #!/usr/bin/env bash
    set -euo pipefail
    VERSION=$(svu next)
    echo "Generating changelog for ${VERSION}..."
    gchlog --write

bump: changelog
    #!/usr/bin/env bash
    set -euo pipefail
    VERSION=$(svu next)
    echo "Bumping to v${VERSION}..."
    git add -A
    git commit -m "chore: release ${VERSION}"
    git push origin main
    git tag "${VERSION}"
    git push origin "${VERSION}"

run:
    @echo "Running the application..."
    python3 test.py -d

