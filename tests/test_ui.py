import re

from app import ui
from app.service import Service


def test_escape_neutraliza_markdown_y_html():
    out = ui.esc("<script>alert(1)</script> **x** [a](http://x) _y_")
    assert not re.search(r"(?<!\\)<", out) and "\\*\\*x\\*\\*" in out and "\\[a\\]\\(" in out


def test_format_reply_incluye_ficha_y_fuentes(cfg):
    d = Service(cfg).responder("horario biblioteca", "todos", "ip", "c")
    md = ui.format_reply(d)
    assert "**Biblioteca**" in md and "**Horario:**" in md and "8:00 a 20:00" in md and "**Teléfono:**" in md


def test_format_reply_escapa_contenido_malicioso():
    d = {"respuesta": "<img src=x onerror=alert(1)>", "fichas": [{"titulo": "<b>T</b>", "puesto": "", "correo": "a_b@x.mx"}],
         "fuentes": [], "advertencias": ["**fuerte**"]}
    md = ui.format_reply(d)
    assert not re.search(r"(?<!\\)<", md) and "a\\_b@x.mx" in md


def test_handle_conversacion(cfg):
    s = Service(cfg)
    hist, _ = ui.handle("¿Cómo solicito una beca?", [], "estudiante", "cid", "1.2.3.4", s)
    assert [m["role"] for m in hist] == ["user", "assistant"] and "Becas" in hist[1]["content"]


def test_handle_vacio_no_cambia(cfg):
    assert ui.handle("   ", [{"role": "assistant", "content": "x"}], "todos", "c", "ip", Service(cfg))[0] == [
        {"role": "assistant", "content": "x"}]


def test_handle_limite_de_ritmo(cfg):
    cfg.req_per_min = 2
    s = Service(cfg)
    last = []
    for _ in range(4):
        last, _ = ui.handle("wifi", last, "todos", "c", "ip", s)
    assert "muchas consultas" in last[-1]["content"]


def test_handle_error_inesperado_no_se_filtra(cfg):
    s = Service(cfg)
    s.responder = lambda *a, **k: 1 / 0
    hist, _ = ui.handle("wifi", [], "todos", "c", "ip", s)
    assert "Ocurrió un error" in hist[-1]["content"] and "Zero" not in hist[-1]["content"]


def test_evento_de_envio_de_gradio(cfg):
    """Ejecuta el manejador real registrado en Gradio (sin request: usa IP '?')."""
    s = Service(cfg)
    demo = ui.build_ui(lambda: s)
    fns = list(demo.fns.values())
    send = next(f for f in fns if len(f.inputs) == 4 and len(f.outputs) == 4)
    hist, caja, _uso, cid = send.fn("horario de la biblioteca", [], "estudiante", None, None)
    assert [m["role"] for m in hist] == ["user", "assistant"]
    assert "Biblioteca" in hist[-1]["content"] and "8:00 a 20:00" in hist[-1]["content"]
    assert caja == "" and cid  # la caja se limpia y se genera un id anónimo
    hist2, _, _, cid2 = send.fn("wifi", hist, "todos", cid, None)
    assert cid2 == cid and len(hist2) == 4

