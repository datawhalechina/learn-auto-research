"""
Evaluator for Project 03.
Runs pytest and counts passing tests.
Contract: print {"pass": bool, "score": float} then exit 0.
"""
import json, re, sys, subprocess

result = subprocess.run(
    [sys.executable, "-m", "pytest", "test_app.py", "-q", "--tb=no", "--color=no"],
    capture_output=True, text=True
)
# Only read pytest's final statistics line, not warning/error text or stderr.
summary_pattern = r"\d+ [a-z]+(?:, \d+ [a-z]+)* in \d+(?:\.\d+)?s(?: \([^)]*\))?"
summary = next(
    (line.strip() for line in reversed(result.stdout.splitlines())
     if re.fullmatch(summary_pattern, line.strip())),
    "",
)
# Mixed summaries start with failures, e.g. "2 failed, 4 passed in 0.01s".
passed_match = re.search(r"\b(\d+) passed\b", summary)
passed_count = int(passed_match.group(1)) if passed_match else 0
total_count = 6

score = round(passed_count / total_count, 4)
passed = result.returncode == 0 and passed_count == total_count

print(json.dumps({"pass": passed, "score": score}))
sys.exit(0)
