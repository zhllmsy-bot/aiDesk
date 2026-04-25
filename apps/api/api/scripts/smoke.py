from __future__ import annotations

import os
import tempfile
import uuid

import httpx


def main() -> None:
    base_url = os.environ.get("AI_DESK_SMOKE_BASE_URL", "http://127.0.0.1:8000")
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"

    with tempfile.TemporaryDirectory(prefix="ai-desk-smoke-") as root_dir:
        register_response = httpx.post(
            f"{base_url}/auth/register",
            json={
                "email": email,
                "password": "super-secure-password",
                "display_name": "Smoke User",
            },
            timeout=10,
        )
        register_response.raise_for_status()
        token = register_response.json()["session"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = httpx.post(
            f"{base_url}/projects",
            json={
                "name": "Smoke Project",
                "root_path": root_dir,
                "default_branch": "main",
            },
            headers=headers,
            timeout=10,
        )
        create_response.raise_for_status()
        project = create_response.json()
        project_id = project["id"]

        list_response = httpx.get(f"{base_url}/projects", headers=headers, timeout=10)
        list_response.raise_for_status()
        detail_response = httpx.get(
            f"{base_url}/projects/{project_id}", headers=headers, timeout=10
        )
        detail_response.raise_for_status()
        print(
            {
                "project_id": project_id,
                "list_total_items": list_response.json()["pagination"]["total_items"],
                "detail_status": detail_response.json()["status"],
            }
        )


if __name__ == "__main__":
    main()
