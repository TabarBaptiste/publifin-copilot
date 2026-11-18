from fastapi.testclient import TestClient

import main


def test_analyses_answer_503_when_the_database_is_unavailable():
    client = TestClient(main.app)  # lifespan not started: no service in app.state

    assert client.post("/analyses", json={"request": "Quimper demande 2 M€"}).status_code == 503
    assert client.get("/analyses/abc").status_code == 503


def test_start_request_is_validated():
    main.app.state.analysis_service = object()  # validation happens before the service is used
    try:
        client = TestClient(main.app)

        assert client.post("/analyses", json={"request": "court"}).status_code == 422
        decision = {"action": "edit", "reviewer": "Baptiste"}
        assert client.post("/analyses/abc/decision", json=decision).status_code == 422
    finally:
        del main.app.state.analysis_service
