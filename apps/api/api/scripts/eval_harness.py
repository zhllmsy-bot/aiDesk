from __future__ import annotations

import json
import sys

from api.observability.evals import run_runtime_regression_suite


def main() -> None:
    result = run_runtime_regression_suite()
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=True))
    if not result.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
