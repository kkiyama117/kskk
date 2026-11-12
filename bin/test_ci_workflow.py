import json
import subprocess
import tempfile
import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "check.yml"
PARENT_GATE = "python3 -m unittest discover -s bin -p 'test_*.py'"
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON = "actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"


def workflow_text():
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def workflow():
    lines = [line for line in workflow_text().splitlines() if not line.strip().startswith("#")]
    return json.loads("\n".join(lines))


class CiWorkflowTest(unittest.TestCase):
    def test_ci_runs_on_pull_requests(self):
        data = workflow()
        self.assertEqual({"pull_request": {}}, data.get("on"))

    def test_ci_avoids_privileged_pull_request_target(self):
        data = workflow()
        self.assertNotIn("pull_request_target", data.get("on") or {})

    def test_ci_token_is_read_only(self):
        data = workflow()
        self.assertEqual({"contents": "read"}, data.get("permissions"))

    def test_ci_jobs_cannot_override_token_permissions(self):
        data = workflow()
        for name, job in data.get("jobs", {}).items():
            self.assertNotIn("permissions", job, name)

    def test_ci_checkout_is_pinned(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        uses = steps[0].get("uses") if steps else None
        self.assertEqual(CHECKOUT, uses)

    def test_ci_checkout_version_comment(self):
        lines = workflow_text().splitlines()
        uses_line = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip().startswith('"uses": "actions/checkout@')
            ),
            None,
        )
        self.assertIsNotNone(uses_line)
        self.assertEqual("# actions/checkout v7.0.1", lines[uses_line - 1].strip())

    def test_ci_checks_out_without_persisting_credentials(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        checkout = steps[0] if steps else {}
        self.assertEqual(False, checkout.get("with", {}).get("persist-credentials"))

    def test_ci_keeps_default_merge_checkout(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        checkout_steps = [
            step for step in steps if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        self.assertEqual(1, len(checkout_steps))
        for step in steps:
            self.assertNotIn("ref", step.get("with", {}))

    def test_ci_python_setup_is_pinned(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        uses = steps[1].get("uses") if len(steps) > 1 else None
        self.assertEqual(SETUP_PYTHON, uses)

    def test_ci_python_setup_version_comment(self):
        lines = workflow_text().splitlines()
        uses_line = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip().startswith('"uses": "actions/setup-python@')
            ),
            None,
        )
        self.assertIsNotNone(uses_line)
        self.assertEqual("# actions/setup-python v7.1.0", lines[uses_line - 1].strip())

    def test_ci_uses_the_selected_python(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        setup = steps[1] if len(steps) > 1 else {}
        version = setup.get("with", {}).get("python-version")
        self.assertEqual("3.15.2", version)
        self.assertIsInstance(version, str)

    def test_ci_workflow_name(self):
        data = workflow()
        self.assertEqual("check", data.get("name"))

    def test_ci_has_only_declared_steps(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        self.assertEqual(3, len(steps))
        self.assertEqual(["uses", "with"], list(steps[0]))
        self.assertEqual(["uses", "with"], list(steps[1]))
        self.assertEqual(["run", "shell"], list(steps[2]))

    def test_ci_job_uses_the_selected_runner(self):
        jobs = workflow().get("jobs", {})
        self.assertEqual(["check"], list(jobs))
        self.assertEqual("ubuntu-latest", jobs.get("check", {}).get("runs-on"))

    def test_ci_runs_the_parent_gate(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        run_steps = [step for step in steps if "run" in step]
        self.assertEqual(1, len(run_steps))
        self.assertEqual(PARENT_GATE, run_steps[0].get("run"))
        self.assertEqual("bash", run_steps[0].get("shell"))

    def test_ci_gate_runs_at_repository_root(self):
        data = workflow()

        def mappings(value):
            if isinstance(value, dict):
                yield value
                for child in value.values():
                    yield from mappings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from mappings(child)

        for mapping in mappings(data):
            self.assertNotIn("defaults", mapping)
            self.assertNotIn("working-directory", mapping)

    def test_ci_cannot_skip_the_gate(self):
        job = workflow().get("jobs", {}).get("check", {})
        gate_steps = [step for step in job.get("steps", []) if "run" in step]
        self.assertTrue(gate_steps)
        self.assertNotIn("if", job)
        for step in gate_steps:
            self.assertNotIn("if", step)

    def test_ci_cannot_ignore_gate_failure(self):
        job = workflow().get("jobs", {}).get("check", {})
        gate_steps = [step for step in job.get("steps", []) if "run" in step]
        self.assertTrue(gate_steps)
        self.assertNotIn("continue-on-error", job)
        for step in gate_steps:
            self.assertNotIn("continue-on-error", step)

    def test_ci_gate_succeeds_on_a_passing_project(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        run_steps = [step for step in steps if "run" in step]
        self.assertTrue(run_steps)
        command = run_steps[0]["run"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bin").mkdir()
            (root / "bin" / "test_sample.py").write_text(
                "import unittest\n\n"
                "class Sample(unittest.TestCase):\n"
                "    def test_passes(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                command,
                cwd=root,
                shell=True,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_ci_gate_fails_on_a_failing_project(self):
        steps = workflow().get("jobs", {}).get("check", {}).get("steps", [])
        run_steps = [step for step in steps if "run" in step]
        self.assertTrue(run_steps)
        command = run_steps[0]["run"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bin").mkdir()
            (root / "bin" / "test_sample.py").write_text(
                "import unittest\n\n"
                "class Sample(unittest.TestCase):\n"
                "    def test_fails(self):\n"
                "        self.fail('synthetic failure')\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                command,
                cwd=root,
                shell=True,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("FAILED", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
