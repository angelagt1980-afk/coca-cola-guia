import pytest
from fastapi.testclient import TestClient

from app import main
from app.service import Service


@pytest.fixture
def client(cfg, monkeypatch):
    monkeypatch.setattr(main.settings, "admin_token", "token-de-prueba")
    main.app.state.service = Service(cfg)
    main._fails.clear()
    yield TestClient(main.app)
    del main.app.state.service


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_home_gradio_y_logo(client):
    r = client.get("/")
    assert r.status_code == 200 and "CampusGuía" in r.text
    assert client.get("/static/logo.png").status_code == 200
    assert client.get("/static/favicon.png").status_code == 200


def test_cabeceras_solo_en_api(client):
    r = client.post("/api/consulta", json={"texto": "wifi"})
    assert "Content-Security-Policy" in r.headers and r.headers["X-Content-Type-Options"] == "nosniff"


def test_consulta_valida(client):
    r = client.post("/api/consulta", json={"texto": "horario biblioteca", "perfil": "todos"})
    assert r.status_code == 200 and r.json()["fichas"]


def test_consulta_invalida_422(client):
    assert client.post("/api/consulta", json={"texto": "", "perfil": "todos"}).status_code == 422
    assert client.post("/api/consulta", json={"texto": "x" * 5000}).status_code == 422
    assert client.post("/api/consulta", json={"texto": "hola", "perfil": "hacker"}).status_code == 422


def test_rate_limit_429(client):
    codes = [client.post("/api/consulta", json={"texto": "wifi"}, headers={"X-Client-Id": "z"}).status_code
             for _ in range(12)]
    assert 429 in codes


def test_admin_requiere_token(client):
    assert client.get("/api/admin/estado").status_code == 401
    ok = client.get("/api/admin/estado", headers={"X-Admin-Token": "token-de-prueba"})
    assert ok.status_code == 200 and ok.json()["entradas"] >= 8
    assert client.post("/api/admin/reindex", headers={"Authorization": "Bearer token-de-prueba"}).status_code == 200


def test_admin_bloquea_tras_intentos(client):
    for _ in range(5):
        client.get("/api/admin/estado", headers={"X-Admin-Token": "mal"})
    assert client.get("/api/admin/estado", headers={"X-Admin-Token": "token-de-prueba"}).status_code == 429
