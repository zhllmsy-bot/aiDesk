from __future__ import annotations

from api.workflows.workers.runtime_worker import main as runtime_worker_main


def main() -> None:
    runtime_worker_main()


if __name__ == "__main__":
    main()
