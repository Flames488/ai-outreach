from fastapi.testclient import TestClient


def test_health_is_always_ok(client: TestClient) -> None:
    """Liveness only — no dependency checks."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_ready_reports_dependency_checks(client: TestClient) -> None:
    """DB/Redis/Celery aren't running in a plain `pytest` invocation, so
    this only asserts the endpoint's shape/contract — not that
    dependencies are up. The "actually reachable" behavior is exercised
    by the docker-compose healthcheck against a live stack.
    """
    response = client.get("/api/v1/ready")

    assert response.status_code in (200, 503)
    body = response.json()
    if response.status_code == 200:
        assert body["success"] is True
        assert set(body["data"]["checks"]) == {"database", "redis", "celery"}
    else:
        assert body["success"] is False
        assert body["errors"][0]["code"] == "NOT_READY"
