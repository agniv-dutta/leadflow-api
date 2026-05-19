from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient


async def register_and_login(client: AsyncClient) -> str:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "StrongPass123!"

    register_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    assert register_response.status_code == 201

    login_response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.mark.anyio
async def test_create_lead(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/leads",
            headers=headers,
            json={
                "name": "Ava Johnson",
                "email": f"ava-{uuid4().hex[:8]}@acme.com",
                "company": "Acme Inc",
                "phone": "+1-555-0100",
                "source": "website",
                "status": "new",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["name"] == "Ava Johnson"
        assert payload["status"] == "new"
        assert payload["email"].endswith("@acme.com")
        assert isinstance(payload["id"], int)


@pytest.mark.anyio
async def test_duplicate_email_rejected(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}
        lead_email = f"dup-{uuid4().hex[:8]}@acme.com"
        lead_payload = {
            "name": "Duplicate Lead",
            "email": lead_email,
            "company": "Acme Inc",
            "phone": "+1-555-0100",
            "source": "website",
            "status": "new",
        }

        first_response = await client.post("/leads", headers=headers, json=lead_payload)
        duplicate_response = await client.post("/leads", headers=headers, json=lead_payload)

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == "A lead with this email already exists."


@pytest.mark.anyio
async def test_status_update_logs_activity(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_response = await client.post(
            "/leads",
            headers=headers,
            json={
                "name": "Status Lead",
                "email": f"status-{uuid4().hex[:8]}@acme.com",
                "company": "Trail Co",
                "phone": "+1-555-0101",
                "source": "referral",
                "status": "new",
            },
        )
        lead_id = create_response.json()["id"]

        update_response = await client.patch(
            f"/leads/{lead_id}/status",
            headers=headers,
            json={"status": "contacted"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "contacted"

        activity_response = await client.get(f"/leads/{lead_id}/activity", headers=headers)
        assert activity_response.status_code == 200
        activity = activity_response.json()
        assert len(activity) == 1
        assert activity[0]["previous_status"] == "new"
        assert activity[0]["new_status"] == "contacted"


@pytest.mark.anyio
async def test_invalid_status_enum_returns_422(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_response = await client.post(
            "/leads",
            headers=headers,
            json={
                "name": "Enum Lead",
                "email": f"enum-{uuid4().hex[:8]}@acme.com",
                "company": "Enum Co",
                "phone": "+1-555-0102",
                "source": "website",
                "status": "new",
            },
        )
        lead_id = create_response.json()["id"]

        response = await client.patch(
            f"/leads/{lead_id}/status",
            headers=headers,
            json={"status": "invalid-status"},
        )

        assert response.status_code == 422


@pytest.mark.anyio
async def test_unknown_lead_id_returns_404(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/leads/999999", headers=headers)

        assert response.status_code == 404
        assert response.json()["detail"] == "Lead not found."