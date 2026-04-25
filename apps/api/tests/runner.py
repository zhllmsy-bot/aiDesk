import subprocess
import sys

result = subprocess.run(
    [sys.executable, "tests/run_security_tests.py"],
    capture_output=True,
    text=True,
    timeout=30,
)
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)
