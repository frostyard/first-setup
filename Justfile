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
    # debian/changelog sets the package version for dpkg-buildpackage, so
    # each release prepends one entry: the commit subjects since the last
    # tag, written with dch (devscripts). The GitHub release page uses
    # GitHub's generated notes (release.yml), not this file.
    VERSION=$(svu next)
    PREV=$(git describe --tags --abbrev=0)
    if [ "${VERSION}" = "${PREV}" ]; then
        echo "No release-worthy commits since ${PREV}." >&2
        exit 1
    fi
    export DEBFULLNAME="${DEBFULLNAME:-$(git config user.name)}"
    export DEBEMAIL="${DEBEMAIL:-$(git config user.email)}"
    echo "Writing debian/changelog entry for ${VERSION}..."
    first=1
    while IFS= read -r subject; do
        if [ "${first}" = 1 ]; then
            dch --newversion "${VERSION#v}" --distribution stable \
                --urgency medium "${subject}"
            first=0
        else
            dch --append "${subject}"
        fi
    done < <(git log --format=%s "${PREV}..HEAD")

bump: changelog
    #!/usr/bin/env bash
    set -euo pipefail
    VERSION=$(svu next)
    echo "Bumping to ${VERSION}..."
    git add -A
    git commit -m "chore: release ${VERSION}"
    git push origin main
    git tag "${VERSION}"
    git push origin "${VERSION}"

run:
    @echo "Running the application..."
    python3 test.py -d

# Workflow contract tests (needs python3-yaml)
test:
    python3 -B -m unittest discover -s tests -v

