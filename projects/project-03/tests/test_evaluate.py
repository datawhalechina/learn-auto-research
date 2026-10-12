"""Run with: python -m unittest discover -s projects/project-03/tests -v."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
STARTER = PROJECT / "starter"


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        for name in ("evaluate.py", "test_app.py"):
            (self.workspace / name).write_bytes((STARTER / name).read_bytes())
        self.env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "-p no:cacheprovider",
        }

    def evaluate(self, app_source):
        (self.workspace / "app.py").write_text(app_source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "evaluate.py"], cwd=self.workspace, env=self.env,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_score_tracks_each_intended_exercise_repair(self):
        source = (STARTER / "app.py").read_text(encoding="utf-8")
        repairs = [
            ('raw["user_id"]', 'raw.get("user_id", "anonymous")'),
            ('raw.get("items", None)', 'raw.get("items", [])'),
            (
                '    return {"user_id": user_id, "amount": amount, "items": items}',
                '    if amount < 0:\n        raise ValueError("negative amount")\n'
                '    return {"user_id": user_id, "amount": amount, "items": items}',
            ),
        ]
        for repaired in range(4):
            with self.subTest(repaired_bugs=repaired):
                self.assertEqual(
                    self.evaluate(source),
                    {"pass": repaired == 3, "score": round((3 + repaired) / 6, 4)},
                )
            if repaired < 3:
                source = source.replace(*repairs[repaired])

    def test_reference_solution_passes(self):
        source = (PROJECT / "solution" / "app.py").read_text(encoding="utf-8")
        self.assertEqual(self.evaluate(source), {"pass": True, "score": 1.0})

    def test_warning_text_does_not_override_the_final_passed_count(self):
        source = (PROJECT / "solution" / "app.py").read_text(encoding="utf-8")
        source += '\nimport warnings\nwarnings.warn("1 passed during an earlier run")\n'
        self.assertEqual(self.evaluate(source), {"pass": True, "score": 1.0})

    def test_collection_error_cannot_pass(self):
        self.assertEqual(self.evaluate("def broken(:\n"), {"pass": False, "score": 0.0})

    def test_collection_error_text_is_not_a_passed_count(self):
        source = 'raise RuntimeError("6 passed during an earlier run")\n'
        self.assertEqual(self.evaluate(source), {"pass": False, "score": 0.0})

    def test_no_passing_tests_scores_zero(self):
        source = (
            'def parse_request(raw):\n    raise RuntimeError("broken")\n'
            'def process_payment(request):\n    raise RuntimeError("broken")\n'
            'def handle(raw):\n    raise RuntimeError("broken")\n'
        )
        self.assertEqual(self.evaluate(source), {"pass": False, "score": 0.0})

    def test_all_failures_ignore_old_passed_count_in_warning(self):
        source = (
            'import warnings\nwarnings.warn("6 passed during an earlier run")\n'
            'def parse_request(raw):\n    raise RuntimeError("broken")\n'
            'def process_payment(request):\n    raise RuntimeError("broken")\n'
            'def handle(raw):\n    raise RuntimeError("broken")\n'
        )
        self.assertEqual(self.evaluate(source), {"pass": False, "score": 0.0})

    def test_pytest_error_after_six_passes_cannot_report_success(self):
        # A failing session-finalization hook still leaves "6 passed" in the summary.
        (self.workspace / "conftest.py").write_text(
            'def pytest_sessionfinish(session, exitstatus):\n'
            '    session.exitstatus = 3\n',
            encoding="utf-8",
        )
        source = (PROJECT / "solution" / "app.py").read_text(encoding="utf-8")
        self.assertEqual(self.evaluate(source), {"pass": False, "score": 1.0})

    def test_stderr_text_does_not_override_pytest_summary(self):
        (self.workspace / "conftest.py").write_text(
            'import sys\ndef pytest_sessionfinish(session, exitstatus):\n'
            '    sys.stderr.write("6 passed during an earlier run\\n")\n',
            encoding="utf-8",
        )
        source = (STARTER / "app.py").read_text(encoding="utf-8")
        self.assertEqual(self.evaluate(source), {"pass": False, "score": 0.5})


if __name__ == "__main__":
    unittest.main()
