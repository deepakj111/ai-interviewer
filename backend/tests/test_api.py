"""Integration tests for FastAPI REST and WebSocket endpoints."""

import pytest
from fastapi import WebSocketDisconnect
from httpx import ASGITransport, AsyncClient

from app.database import init_db
from app.main import app
from app.services.gemini_live import LiveInterviewSessionHandler


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
        assert len(questions) == 21

        # Filter by SQL
        sql_resp = await ac.get("/api/questions?category=SQL")
        assert sql_resp.status_code == 200
        sql_q = sql_resp.json()
        assert len(sql_q) == 7

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
        assert 0.0 <= eval_data["overall_score"] <= 5.0
        assert "No Hire" in eval_data["recommendation"]
        assert len(eval_data["question_critiques"]) >= 1

        # 5. Fetch saved report
        report_resp = await ac.get(f"/api/session/{session_id}/report")
        assert report_resp.status_code == 200
        assert report_resp.json()["overall_score"] == eval_data["overall_score"]

        # 6. Test switch question endpoint
        switch_resp = await ac.post(f"/api/session/{session_id}/switch_question?category=SQL")
        assert switch_resp.status_code == 200
        switch_data = switch_resp.json()
        assert switch_data["status"] == "success"
        assert switch_data["new_question"]["category"] == "SQL"


class MockWebSocket:
    """Lightweight asynchronous mock for WebSocket transport."""

    def __init__(self, incoming_messages):
        self.incoming = list(incoming_messages)
        self.sent_messages = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def receive_json(self):
        if self.incoming:
            return self.incoming.pop(0)
        raise WebSocketDisconnect(code=1000)


@pytest.mark.asyncio
async def test_websocket_interview_simulation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        init_res = await ac.post(
            "/api/session/init",
            data={"target_role": "Senior ML Engineer", "interview_mode": "FULL_LOOP"},
        )
        assert init_res.status_code == 200
        session_id = init_res.json()["session_id"]

    mock_ws = MockWebSocket(
        [
            {
                "type": "text_turn",
                "text": "I led the development of a real-time ranking engine with 10ms SLA.",
            },
            {"type": "close"},
        ]
    )

    handler = LiveInterviewSessionHandler(
        websocket=mock_ws,  # type: ignore[arg-type]
        session_id=session_id,
    )
    await handler.handle_client()

    assert mock_ws.accepted is True
    msg_types = [m.get("type") for m in mock_ws.sent_messages]
    assert "fsm_snapshot" in msg_types
    assert "transcript_caption" in msg_types


@pytest.mark.asyncio
async def test_recent_real_world_questions_api():
    """Verify GET /api/questions/recent_real_world returns real company questions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            "/api/questions/recent_real_world?company=Swiggy&role=Senior+ML+Engineer&track=ML_SYSTEM_DESIGN"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["company"] == "Swiggy"
        assert len(data["questions"]) >= 2
