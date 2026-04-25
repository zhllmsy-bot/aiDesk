from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from api.config import Settings


def create_user(client: TestClient, email: str, display_name: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "super-secure-password",
            "display_name": display_name,
        },
    )
    token = response.json()["session"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_projects_require_authentication(client: TestClient) -> None:
    response = client.get("/projects")
    assert response.status_code == 401


def test_create_list_detail_archive_and_pagination(
    client: TestClient,
    project_root: Path,
    maintainer_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/projects",
        json={
            "name": "Project Alpha",
            "root_path": str(project_root),
            "default_branch": "main",
            "description": "Primary workspace",
        },
        headers=maintainer_headers,
    )
    assert create_response.status_code == 201
    project = create_response.json()
    project_id = project["id"]
    assert project["current_user_role"] == "admin"

    list_response = client.get(
        "/projects?page=1&page_size=10&sort_by=name&sort_order=asc", headers=maintainer_headers
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["pagination"]["total_items"] == 1
    assert list_payload["items"][0]["id"] == project_id

    detail_response = client.get(f"/projects/{project_id}", headers=maintainer_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["membership_counts"]["admin"] == 1

    archive_response = client.post(f"/projects/{project_id}/archive", headers=maintainer_headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    filtered_list = client.get("/projects?status=archived", headers=maintainer_headers)
    assert filtered_list.status_code == 200
    assert filtered_list.json()["pagination"]["total_items"] == 1


def test_duplicate_project_root_path_is_rejected(
    client: TestClient,
    project_root: Path,
    maintainer_headers: dict[str, str],
) -> None:
    first = client.post(
        "/projects",
        json={"name": "Project Alpha", "root_path": str(project_root), "default_branch": "main"},
        headers=maintainer_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/projects",
        json={"name": "Project Beta", "root_path": str(project_root), "default_branch": "main"},
        headers=maintainer_headers,
    )
    assert second.status_code == 409


def test_viewer_cannot_archive_project(client: TestClient, tmp_path: Path) -> None:
    owner_headers = create_user(client, "owner@example.com", "Owner")
    viewer_headers = create_user(client, "viewer@example.com", "Viewer")

    owner_root = tmp_path / "owner-root"
    owner_root.mkdir()
    create_response = client.post(
        "/projects",
        json={"name": "Protected Project", "root_path": str(owner_root), "default_branch": "main"},
        headers=owner_headers,
    )
    project_id = create_response.json()["id"]

    get_me_response = client.get("/auth/me", headers=viewer_headers)
    viewer_id = get_me_response.json()["user"]["id"]

    from api.control_plane.models import MembershipStatus, ProjectMembership, ProjectRole
    from api.database import create_session_factory

    settings = cast(Settings, client.app_state["settings"])
    session_factory = create_session_factory(settings.database_url)
    session = session_factory()
    try:
        session.add(
            ProjectMembership(
                project_id=project_id,
                user_id=viewer_id,
                role=ProjectRole.viewer,
                status=MembershipStatus.active,
            )
        )
        session.commit()
    finally:
        session.close()

    archive_response = client.post(f"/projects/{project_id}/archive", headers=viewer_headers)
    assert archive_response.status_code == 403
