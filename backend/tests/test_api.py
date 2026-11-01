"""Integration tests for FastAPI REST and WebSocket endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(autouse=True)
async def setup_database():
    """Ensure database schema is created for tests."""
    await init_db()


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_questions_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/questions")
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) == 15

        # Filter by SQL
        sql_resp = await ac.get("/api/questions?category=SQL")
        assert sql_resp.status_code == 200
        sql_q = sql_resp.json()
        assert len(sql_q) == 5

        # Get specific question
        single_resp = await ac.get("/api/questions/sql_01_retention_cohort")
        assert single_resp.status_code == 200
        assert single_resp.json()["id"] == "sql_01_retention_cohort"


@pytest.mark.asyncio
async def test_session_lifecycle_and_evaluation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Initialize session without file
        init_resp = await ac.post(
            "/api/session/init",
            data={
                "target_role": "Senior Applied Scientist",
                "target_company": "Google",
                "interview_mode": "FULL_LOOP",
            },
        )
        assert init_resp.status_code == 200
        init_data = init_resp.json()
        session_id = init_data["session_id"]
        assert session_id is not None
        assert init_data["initial_stage"] == "INTRO"

        # 2. Retrieve session
        get_resp = await ac.get(f"/api/session/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

        # 3. Advance stage
        adv_resp = await ac.post(f"/api/session/{session_id}/advance_stage")
        assert adv_resp.status_code == 200
        assert adv_resp.json()["new_stage"] == "RESUME_DEEP_DIVE"

        # 4. Evaluate session
        eval_resp = await ac.post(f"/api/session/{session_id}/evaluate")
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert 1.0 <= eval_data["overall_score"] <= 5.0
        assert len(eval_data["question_critiques"]) >= 1

        # 5. Fetch saved report
        report_resp = await ac.get(f"/api/session/{session_id}/report")
        assert report_resp.status_code == 200
        assert report_resp.json()["overall_score"] == eval_data["overall_score"]


def test_websocket_interview_simulation():
    # Create session synchronously using test client
    client = TestClient(app)
    init_res = client.post(
        "/api/session/init",
        data={"target_role": "Senior ML Engineer", "interview_mode": "FULL_LOOP"},
    )
    assert init_res.status_code == 200
    session_id = init_res.json()["session_id"]

    # Connect to WebSocket
    with client.websocket_connect(f"/ws/interview/{session_id}") as websocket:
        # Receive FSM snapshot
        snapshot_msg = websocket.receive_json()
        assert snapshot_msg["type"] == "fsm_snapshot"

        # Receive greeting caption
        caption_msg = websocket.receive_json()
        assert caption_msg["type"] == "transcript_caption"
        assert caption_msg["speaker"] == "interviewer"

        # Send candidate answer
        websocket.send_json(
            {
                "type": "text_turn",
                "text": "I led the development of a real-time ranking engine with 10ms SLA.",
            }
        )
        reply_msg = websocket.receive_json()
        assert reply_msg["type"] == "transcript_caption"
