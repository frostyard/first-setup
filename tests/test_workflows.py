"""Contract tests for the GitHub workflows.

A version tag releases snow-first-setup and asks frostyard/apt-publisher, the
single writer of the Debian repository (frostyard/core ADR-0055), to publish
it. apt-publisher then asks frostyard/snosi to rebuild (ADR-0056). Every
action is pinned to a commit SHA, with least-privilege permissions
(ADR-0021).

Run with: python3 -B -m unittest discover -s tests -v
Needs PyYAML (Debian: python3-yaml).
"""

import json
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
BUILD = ROOT / ".github" / "workflows" / "build.yml"

USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s+#\s*v\d")


def load(path):
    with open(path, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)
    # YAML 1.1 reads the key `on` as the boolean true.
    if True in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


def all_steps(workflow):
    for job_id, job in workflow["jobs"].items():
        for index, step in enumerate(job.get("steps", [])):
            yield job_id, job, index, step


def action(step):
    return step.get("uses", "").split("@")[0]


class ActionPinningTest(unittest.TestCase):
    def test_every_action_is_pinned_to_a_commit_sha(self):
        for path in WORKFLOWS:
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                match = USES.match(line)
                if not match:
                    continue
                ref = match["ref"].strip("'\"")
                if ref.startswith("./"):
                    continue
                with self.subTest(file=path.name, line=number):
                    self.assertRegex(
                        ref, PINNED, f"{path.name}:{number}: {ref} is not pinned to a full commit SHA"
                    )
                    self.assertRegex(
                        match["rest"],
                        VERSION_COMMENT,
                        f"{path.name}:{number}: {ref} needs a trailing '# vX.Y.Z' comment",
                    )

    def test_workflows_declare_permissions(self):
        for path in WORKFLOWS:
            with self.subTest(file=path.name):
                self.assertIn("permissions", load(path), f"{path.name} has no top-level permissions")

    def test_checkouts_do_not_persist_credentials(self):
        for path in WORKFLOWS:
            for job_id, _, index, step in all_steps(load(path)):
                if action(step) != "actions/checkout":
                    continue
                with self.subTest(file=path.name, job=job_id, step=index):
                    self.assertIs(step.get("with", {}).get("persist-credentials"), False)

    def test_expressions_reach_shell_only_through_env(self):
        for path in WORKFLOWS:
            for job_id, _, index, step in all_steps(load(path)):
                with self.subTest(file=path.name, job=job_id, step=index):
                    self.assertNotIn("${{", step.get("run", ""), "pass values to run: through env:")


class ReleaseWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = load(RELEASE)
        cls.jobs = cls.workflow["jobs"]
        # Comments dropped, so prose about snosi or repogen doesn't count.
        cls.body = yaml.safe_dump(cls.workflow)

    def find(self, predicate, what):
        found = [(job_id, index, step) for job_id, _, index, step in all_steps(self.workflow) if predicate(step)]
        self.assertEqual(len(found), 1, f"release.yml needs exactly one {what} step, found {len(found)}")
        return found[0]

    def ancestors(self, job_id):
        needs = self.jobs[job_id].get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        result = set(needs)
        for need in needs:
            result |= self.ancestors(need)
        return result

    def comes_before(self, first, second):
        (first_job, first_index, _), (second_job, second_index, _) = first, second
        if first_job == second_job:
            return first_index < second_index
        return first_job in self.ancestors(second_job)

    def dispatch(self):
        return self.find(lambda s: action(s) == "peter-evans/repository-dispatch", "repository-dispatch")

    def release(self):
        return self.find(lambda s: "gh release create" in s.get("run", ""), "gh release create")

    def attest(self):
        return self.find(lambda s: action(s) == "actions/attest-build-provenance", "attest-build-provenance")

    def test_runs_only_for_version_tags(self):
        self.assertEqual(self.workflow["on"], {"push": {"tags": ["v*"]}})

    def test_requests_apt_publication(self):
        _, _, step = self.dispatch()
        inputs = step["with"]
        self.assertEqual(inputs["token"], "${{ secrets.APT_PUBLISH_TOKEN }}")
        self.assertEqual(inputs["repository"], "frostyard/apt-publisher")
        self.assertEqual(inputs["event-type"], "publish-deb")
        self.assertEqual(
            json.loads(inputs["client-payload"]),
            {"repo": "${{ github.repository }}", "tag": "${{ github.ref_name }}"},
        )

    def test_publication_request_is_unconditional_and_last(self):
        job_id, index, step = self.dispatch()
        job = self.jobs[job_id]
        for where, mapping in (("job", job), ("step", step)):
            with self.subTest(where=where):
                self.assertNotIn("if", mapping, f"the publication request {where} must not be conditional")
                self.assertNotIn(
                    "continue-on-error", mapping, f"a failed publication request must fail the release ({where})"
                )
        self.assertEqual(index, len(job["steps"]) - 1, "the publication request must be its job's last step")
        others = [other for other in self.jobs if other != job_id]
        self.assertEqual(self.ancestors(job_id), set(others), "the publication request must run after every job")

    def test_publication_is_requested_after_the_release_exists(self):
        self.assertTrue(self.comes_before(self.release(), self.dispatch()))

    def test_assets_are_attested_before_the_release_is_created(self):
        attest, release = self.attest(), self.release()
        self.assertTrue(self.comes_before(attest, release))
        subjects = attest[2]["with"]["subject-path"].split()
        self.assertIn("dist/*.deb", subjects)
        self.assertIn("dist/*.deb", release[2]["run"])
        permissions = self.jobs[attest[0]]["permissions"]
        self.assertEqual(permissions.get("id-token"), "write")
        self.assertEqual(permissions.get("attestations"), "write")

    def test_tag_must_match_debian_changelog_before_building(self):
        guard = self.find(
            lambda s: "dpkg-parsechangelog" in s.get("run", "") and '"v$version"' in s.get("run", ""),
            "tag/changelog check",
        )
        build = self.find(lambda s: "dpkg-buildpackage" in s.get("run", ""), "dpkg-buildpackage")
        self.assertTrue(self.comes_before(guard, build))

    def test_release_asset_names_carry_the_version(self):
        # apt-publisher publishes each .deb under its asset name, and its audit
        # parses name_version_arch.deb. The unversioned name would collide in
        # the pool with 0.1.1's snow-first-setup.deb.
        self.assertNotIn("snow-first-setup.deb", self.body)

    def test_does_not_publish_or_rebuild_directly(self):
        for needle in ("repogen", "frostyard/snosi", "R2_", "REPOGEN_GPG_KEY", "CLOUDFLARE_", "ORG_PAT"):
            with self.subTest(needle=needle):
                self.assertNotIn(needle, self.body)
        for job_id, _, index, step in all_steps(self.workflow):
            with self.subTest(job=job_id, step=index):
                self.assertNotEqual(step.get("with", {}).get("event-type"), "build")


class BuildWorkflowTest(unittest.TestCase):
    def test_continuous_prerelease_only_from_main(self):
        steps = [step for _, _, _, step in all_steps(load(BUILD)) if action(step) == "softprops/action-gh-release"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].get("if"), "github.ref == 'refs/heads/main'")
        self.assertEqual(steps[0]["with"]["tag_name"], "continuous")
        self.assertIs(steps[0]["with"]["prerelease"], True)


if __name__ == "__main__":
    unittest.main()
