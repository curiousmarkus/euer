import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION_RE = re.compile(r"uses:\s+[^@\s]+@([0-9a-f]{40})$")


class WorkflowTestCase(unittest.TestCase):
    def test_all_repository_actions_are_pinned_to_full_shas(self) -> None:
        workflow_files = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))

        self.assertTrue(workflow_files)
        for workflow in workflow_files:
            for line_number, line in enumerate(
                workflow.read_text(encoding="utf-8").splitlines(), 1
            ):
                if "uses:" not in line:
                    continue
                self.assertRegex(
                    line.strip(),
                    PINNED_ACTION_RE,
                    f"{workflow}:{line_number} ist nicht auf einen vollständigen SHA gepinnt",
                )

    def test_release_workflow_keeps_publish_order_and_recovery_invariants(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        for job in ("validate:", "test:", "build:", "verify-artifacts:", "github-draft:"):
            self.assertIn(job, workflow)
        self.assertIn("needs: github-draft", workflow)
        self.assertIn("needs: publish-pypi", workflow)
        publish_github = workflow.split("  publish-github:", 1)[1]
        self.assertIn("uses: actions/checkout@", publish_github)
        self.assertIn("skip-existing: false", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("attestations: true", workflow)
        self.assertEqual(
            2,
            workflow.count(
                'git fetch --force origin "refs/tags/${GITHUB_REF_NAME}:refs/tags/${GITHUB_REF_NAME}"'
            ),
        )
        self.assertIn('gh release view "$RELEASE_TAG" --json databaseId', workflow)
        self.assertNotIn("releases/tags/${RELEASE_TAG}", workflow)
