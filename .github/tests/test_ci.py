"""Behavior tests for repository CI filters and validators; stdlib only."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ci_changes", ROOT / ".github/scripts/ci-changes.py")
changes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changes)


class ChangeDetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = os.getcwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, previous)
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci@example.invalid")
        Path("README.md").write_text("Initial\n")
        Path("settings.yaml").write_text("enabled: true\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def check(self, docs, config):
        self.assertEqual(changes.selected_checks("pull_request", self.base, self.commit()),
                         {"docs": docs, "config": config})

    def test_docs_only(self):
        Path("README.md").write_text("Updated\n")
        self.check(True, False)

    def test_yaml_only(self):
        Path("settings.yaml").write_text("enabled: false\n")
        self.check(False, True)

    def test_mixed(self):
        Path("README.md").write_text("Updated\n")
        Path("settings.yaml").write_text("enabled: false\n")
        self.check(True, True)

    def test_source_or_image_only_skips_repository_checks(self):
        Path("Example.java").write_text("class Example {}\n")
        Path("diagram.png").write_bytes(b"image fixture")
        self.check(False, False)

    def test_deleted_docs(self):
        Path("README.md").unlink()
        self.check(True, False)

    def test_rename_doc_to_yaml_checks_both_paths(self):
        Path("README.md").rename("new.yaml")
        self.check(True, True)

    def test_validator_and_shared_detector(self):
        for name in ["validate-markdown.rb", "ci-changes.py"]:
            file = Path(".github/scripts") / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# fixture\n")
            self.check(True, True)

    def test_manual_and_missing_baselines(self):
        expected = {"docs": True, "config": True}
        self.assertEqual(changes.selected_checks("workflow_dispatch", self.base, self.base), expected)
        for base in ["", "0" * 40, "f" * 40]:
            self.assertEqual(changes.selected_checks("push", base, self.base), expected)

    def test_workflow_outputs(self):
        Path("README.md").write_text("Updated\n")
        head = self.commit()
        output = Path("outputs.txt").resolve()
        subprocess.run(["python3", str(ROOT / ".github/scripts/ci-changes.py")], check=True,
                       capture_output=True, env={**os.environ, "EVENT_NAME": "pull_request",
                       "BASE_SHA": self.base, "HEAD_SHA": head, "GITHUB_OUTPUT": str(output)})
        self.assertEqual(output.read_text().splitlines(),
                         ["should-run-docs=true", "should-run-config=false"])


class ValidatorTests(unittest.TestCase):
    def validate(self, kind, path, content):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github").mkdir()
            shutil.copy(ROOT / f".github/{kind}-validation.yml", root / ".github")
            file = root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)
            return subprocess.run(
                ["ruby", str(ROOT / f".github/scripts/validate-{kind}.rb")],
                cwd=root, capture_output=True,
            )

    def test_markdown_passes_valid_fences(self):
        result = self.validate("markdown", ".github/CI.md", b"# CI\n\n```sh\nmake test\n```\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_markdown_rejects_invalid_content(self):
        for content in [b"# Bad\n\xff", b"<<<<<<< HEAD\n", b"```swift\nunfinished\n"]:
            with self.subTest(content=content):
                self.assertNotEqual(self.validate("markdown", "docs/guide.md", content).returncode, 0)

    def test_yaml_passes_workflow_and_reusable_job(self):
        content = b"name: Test\non: push\njobs:\n  test:\n    uses: owner/repo/.github/workflows/test.yml@main\n"
        result = self.validate("yaml", ".github/workflows/test.yml", content)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_yaml_rejects_syntax_and_missing_workflow_fields(self):
        for content in [b"name: [broken", b"name: Test\non: push\n",
                        b"name: Test\non: push\njobs:\n  test:\n    steps: []\n"]:
            with self.subTest(content=content):
                self.assertNotEqual(self.validate("yaml", ".github/workflows/test.yml", content).returncode, 0)


if __name__ == "__main__":
    unittest.main()
