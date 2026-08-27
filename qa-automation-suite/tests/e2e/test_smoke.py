def test_health_check(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_is_served(api_client):
    response = api_client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_docs_reachable(api_client):
    response = api_client.get("/docs")

    assert response.status_code == 200
