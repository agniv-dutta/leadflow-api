from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

import auth as auth_module
import main
from database import get_db


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


@pytest.mark.anyio
async def test_list_leads_supports_pagination_and_search(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        lead_rows = [
            ("Alpha One", f"alpha-{uuid4().hex[:8]}@acme.com", "Acme Alpha"),
            ("Beta Two", f"beta-{uuid4().hex[:8]}@acme.com", "Beta Works"),
            ("Gamma Three", f"gamma-{uuid4().hex[:8]}@acme.com", "Gamma LLC"),
        ]
        for name, email, company in lead_rows:
            response = await client.post(
                "/leads",
                headers=headers,
                json={
                    "name": name,
                    "email": email,
                    "company": company,
                    "phone": "+1-555-0100",
                    "source": "website",
                    "status": "new",
                },
            )
            assert response.status_code == 201

        paginated = await client.get("/leads?page=1&page_size=2&status=new", headers=headers)
        paginated_payload = paginated.json()
        assert paginated.status_code == 200
        assert paginated_payload["total"] == 3
        assert paginated_payload["page"] == 1
        assert paginated_payload["page_size"] == 2
        assert len(paginated_payload["results"]) == 2

        searched = await client.get("/leads?search=beta", headers=headers)
        searched_payload = searched.json()
        assert searched.status_code == 200
        assert searched_payload["total"] == 1
        assert len(searched_payload["results"]) == 1
        assert searched_payload["results"][0]["company"] == "Beta Works"


def test_database_get_db_yields_a_session(test_engine):
    session_generator = get_db()
    session = next(session_generator)
    assert session is not None
    session_generator.close()


def test_auth_helpers_handle_invalid_credentials_and_tokens():
    class EmptyQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class EmptySession:
        def query(self, model):
            return EmptyQuery()

    empty_session = EmptySession()

    assert auth_module.authenticate_user(empty_session, "missing@example.com", "password") is None

    with pytest.raises(HTTPException) as missing_credentials:
        auth_module.get_current_user(credentials=None, db=empty_session)
    assert missing_credentials.value.status_code == 401

    invalid_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    with pytest.raises(HTTPException) as invalid_token:
        auth_module.get_current_user(credentials=invalid_credentials, db=empty_session)
    assert invalid_token.value.status_code == 401

    valid_token = auth_module.create_access_token(subject="missing@example.com")
    valid_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)
    with pytest.raises(HTTPException) as missing_user:
        auth_module.get_current_user(credentials=valid_credentials, db=empty_session)
    assert missing_user.value.status_code == 401


@pytest.mark.anyio
async def test_health_and_exception_handlers_cover_error_paths():
    class HealthySession:
        def execute(self, statement):
            return object()

    class BrokenSession:
        def execute(self, statement):
            raise SQLAlchemyError("boom")

    assert main.health_check(db=HealthySession()) == {"status": "ok", "database": {"connected": True}}

    degraded = main.health_check(db=BrokenSession())
    assert degraded.status_code == 503

    http_exception_response = await main.http_exception_handler(
        None,
        HTTPException(status_code=418, detail="teapot"),
    )
    assert http_exception_response.status_code == 418

    unhandled_response = await main.unhandled_exception_handler(None, Exception("boom"))
    assert unhandled_response.status_code == 500