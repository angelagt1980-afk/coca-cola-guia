import json

import httpx
import pytest

from app import admin, llm
from app.admin import Admin, build_admin_ui, publicar_github
from app.config import BASE
from app.service import Service

TOK = "token-de-prueba"
IP = "9.9.9.9"


@pytest.fixture
def ad(cfg, tmp_path):
    cfg.corpus_path = tmp_path / "corpus.txt"
    cfg.corpus_path.write_text((BASE / "data" / "corpus.txt").read_text("utf-8"), "utf-8")
    cfg.index_path = tmp_path / "index.json"
    s = Service(cfg)
    return Admin(lambda: s, cfg), s, cfg


def test_guard_token_y_bloqueo(ad):
    a, _, cfg = ad
    a.guard(TOK, IP)
    with pytest.raises(PermissionError, match="inválido"):
        a.guard("mal", IP)
    for _ in range(4):
        with pytest.raises(PermissionError):
            a.guard("mal", IP)
    with pytest.raises(PermissionError, match="Demasiados"):
        a.guard(TOK, IP)            # bloqueado aunque el token sea correcto
    a.guard(TOK, "1.1.1.1")         # otra IP no se ve afectada
    cfg.admin_token = ""
    with pytest.raises(PermissionError, match="deshabilitada"):
        Admin(lambda: None, cfg).guard("", "x")


def test_resumen_escapa_contenido_de_usuarios(ad):
    a, s, _ = ad
    s.responder("wifi", "todos", "ip", "c")
    s.reportar("<img src=x onerror=alert(1)> **negrita**", "ip", "c")
    md = a.resumen(TOK, IP)
    assert "Temas más consultados" in md and "Soporte Técnico" in md and "negrita" in md
    assert "<img" not in md.replace("\\<img", "")
    with pytest.raises(PermissionError):
        a.resumen("mal", IP)


def test_validar(ad):
    a, _, _ = ad
    ok = a.validar((BASE / "data" / "corpus.txt").read_text("utf-8"), TOK, IP)
    assert "10 fichas válidas · 0 errores" in ok
    assert "1 errores" in a.validar("### sin-titulo\nTAGS: a\n--\nx", TOK, IP)


def test_guardar_escribe_reindexa_y_avisa_si_no_hay_github(ad):
    a, s, cfg = ad
    nuevo = cfg.corpus_path.read_text("utf-8") + "\n\n### gimnasio\nTITULO: Gimnasio\nTAGS: gimnasio, deporte\nACTUALIZADO: 2026-10-11\n--\nAbre de 7 a 20 h.\n"
    msg = a.guardar(nuevo, TOK, IP)
    assert "11 fichas" in msg and "GitHub no está configurado" in msg
    assert "gimnasio" in cfg.corpus_path.read_text("utf-8")
    assert "gimnasio" in s._by_id                        # ya está activo sin reiniciar
    assert s.responder("gimnasio", "todos", "ip", "c")["entrada_id"] == "gimnasio"


def test_guardar_rechaza_errores_y_pendientes(ad):
    a, _, cfg = ad
    antes = cfg.corpus_path.read_text("utf-8")
    assert "No se guardó" in a.guardar("### x\nTAGS: a\n--\nsin titulo", TOK, IP)
    pendiente = antes + "\n\n### nuevo\nTITULO: Nuevo\nTAGS: a\n--\n[COMPLETAR con la información oficial]\n"
    assert "COMPLETAR" in a.guardar(pendiente, TOK, IP)
    assert cfg.corpus_path.read_text("utf-8") == antes   # nada cambió
    assert "tamaño máximo" in a.guardar("x" * 500_000, TOK, IP)
    with pytest.raises(PermissionError):
        a.guardar(antes, "mal", IP)


def test_publicar_github_ok_con_y_sin_sha(cfg, monkeypatch):
    cfg.github_token, cfg.github_repo, cfg.github_branch = "ghp_x", "usuario/repo", "main"
    puestos = []
    estado = {"get": 200}

    def get(url, headers, params, timeout):
        assert url.endswith("/repos/usuario/repo/contents/data/corpus.txt") and headers["Authorization"] == "Bearer ghp_x"
        return httpx.Response(estado["get"], json={"sha": "abc123"} if estado["get"] == 200 else {}, request=httpx.Request("GET", url))

    def put(url, headers, json, timeout):
        puestos.append(json)
        return httpx.Response(200, json={"commit": {"sha": "deadbeefcafe"}}, request=httpx.Request("PUT", url))
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx, "put", put)
    assert "commit deadbee" in publicar_github("contenido ñ", cfg)
    assert puestos[0]["sha"] == "abc123" and puestos[0]["branch"] == "main"
    import base64
    assert base64.b64decode(puestos[0]["content"]).decode() == "contenido ñ"
    estado["get"] = 404                                   # archivo nuevo: sin sha
    publicar_github("x", cfg)
    assert "sha" not in puestos[1]


def test_publicar_github_errores(cfg, monkeypatch):
    cfg.github_token, cfg.github_repo = "ghp_x", "usuario/repo"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(401, json={}, request=httpx.Request("GET", "http://x")))
    assert "No se pudo leer" in publicar_github("x", cfg)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={"sha": "s"}, request=httpx.Request("GET", "http://x")))
    monkeypatch.setattr(httpx, "put", lambda *a, **k: httpx.Response(403, json={}, request=httpx.Request("PUT", "http://x")))
    assert "rechazó" in publicar_github("x", cfg)

    def cae(*a, **k):
        raise httpx.ConnectError("sin red")
    monkeypatch.setattr(httpx, "get", cae)
    assert "No se pudo conectar" in publicar_github("x", cfg)
    cfg.github_token = ""
    assert "no está configurado" in publicar_github("x", cfg)


def test_importar_y_borrador_desde_el_panel(ad, tmp_path, monkeypatch):
    a, s, cfg = ad
    doc = tmp_path / "idiomas.txt"
    doc.write_text("Servicio de Idiomas. Cursos de inglés y francés. Informes en la ventanilla 4. " * 2, "utf-8")
    assert a.importar(None, TOK, IP)[1] == "Sube un archivo primero."
    assert "LLM_API_KEY" in a.importar(str(doc), TOK, IP)[1]            # sin IA configurada
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    ficha = "### idiomas\nTITULO: Idiomas\nTAGS: idiomas, ingles\nPREGUNTA: ¿Cómo me inscribo a inglés?\n--\nCursos de inglés y francés."
    monkeypatch.setattr(llm, "complete", lambda s_, sy, u, m: (ficha, 500, 100))
    prop, res = a.importar(str(doc), TOK, IP)
    assert "### idiomas" in prop and "1 fichas propuestas" in res and "500 entrada + 100 salida" in res
    assert "No se pudo leer" in a.importar(str(tmp_path / "no_existe.txt"), TOK, IP)[1]
    assert "Aún no hay informes" in a.borrador(TOK, IP)[1]
    s.reportar("horario del gimnasio", "ip", "c")
    monkeypatch.setattr(llm, "complete", lambda s_, sy, u, m: ("### gimnasio\nTITULO: Gimnasio\nTAGS: gimnasio\n--\n[COMPLETAR]", 100, 50))
    prop2, res2 = a.borrador(TOK, IP)
    assert "[COMPLETAR" in prop2 and "1 fichas propuestas" in res2

    def falla(*args):
        raise llm.LLMError("caído")
    monkeypatch.setattr(llm, "complete", falla)
    assert "Falló la llamada" in a.importar(str(doc), TOK, IP)[1] and "Falló la llamada" in a.borrador(TOK, IP)[1]
    with pytest.raises(PermissionError):
        a.importar(str(doc), "mal", IP)


def test_pantalla_de_acceso_del_panel(ad):
    _a, s, cfg = ad
    demo = build_admin_ui(lambda: s, cfg)
    login = next(f for f in demo.fns.values() if len(f.inputs) == 1 and len(f.outputs) == 6)
    mal = login.fn("mal", None)
    assert mal[1] == gr_update_vacio() and mal[2] == "" and "inválido" in mal[3]       # no revela el panel
    bien = login.fn(cfg.admin_token, None)
    assert bien[0]["visible"] is False and bien[1]["visible"] is True and bien[2] == cfg.admin_token
    assert "Entradas" in bien[4] and "### servicios-escolares" in bien[5]


def gr_update_vacio():
    import gradio as gr
    return gr.update()


def test_boton_del_panel_sin_token_valido_da_error(ad):
    import gradio as gr
    _, s, cfg = ad
    demo = build_admin_ui(lambda: s, cfg)
    guardar = next(f for f in demo.fns.values() if len(f.inputs) == 2 and len(f.outputs) == 1 and f.fn.__name__ == "h_guardar")
    with pytest.raises(gr.Error):
        guardar.fn("### x", "token-malo", None)


def test_modulo_exporta_css_admin():
    assert "#editor" in admin.ADMIN_CSS and json.dumps(admin.MAX_CORPUS_CHARS)
