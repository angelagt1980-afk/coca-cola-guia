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
    hist, _, sin = ui.handle("¿Cómo solicito una beca?", [], "cid", "1.2.3.4", Service(cfg))
    assert [m["role"] for m in hist] == ["user", "assistant"] and "Becas" in hist[1]["content"] and sin == ""


def test_handle_sin_informacion_marca_pregunta_para_informar(cfg):
    hist, _, sin = ui.handle("cuanto cuesta un boleto de avion a Paris", [], "c", "ip", Service(cfg))
    assert sin.startswith("cuanto cuesta") and "No encontré" in hist[-1]["content"]


def test_handle_vacio_no_cambia(cfg):
    base = [{"role": "assistant", "content": "x"}]
    assert ui.handle("   ", base, "c", "ip", Service(cfg)) == (base, "", "")


def test_handle_limite_de_ritmo(cfg):
    cfg.req_per_min = 2
    s = Service(cfg)
    last = []
    for _ in range(4):
        last, _, _ = ui.handle("wifi", last, "c", "ip", s)
    assert "muchas consultas" in last[-1]["content"]


def test_handle_error_inesperado_no_se_filtra(cfg):
    s = Service(cfg)
    s.responder = lambda *a, **k: 1 / 0
    hist, _, _ = ui.handle("wifi", [], "c", "ip", s)
    assert "Ocurrió un error" in hist[-1]["content"] and "Zero" not in hist[-1]["content"]


def _fn(demo, n_in):
    return next(f for f in demo.fns.values() if len(f.inputs) == n_in and len(f.outputs) >= 4)


def test_evento_de_envio_de_gradio(cfg):
    """Ejecuta el manejador real registrado en Gradio (sin request: usa IP '?')."""
    s = Service(cfg)
    demo = ui.build_ui(lambda: s)
    send = _fn(demo, 3)
    hist, caja, _uso, cid, chips, report, sin = send.fn("horario de la biblioteca", [], None, None)
    assert [m["role"] for m in hist] == ["user", "assistant"] and "8:00 a 20:00" in hist[-1]["content"]
    assert caja == "" and cid and sin == ""
    assert chips["visible"] is False and report["visible"] is False  # tras preguntar se ocultan los ejemplos
    _h2, *_rest, report2, sin2 = send.fn("cuanto cuesta un vuelo a Paris", hist, cid, None)
    assert report2["visible"] is True and sin2.startswith("cuanto cuesta")  # aparece el botón de informe


def test_boton_de_informe_registra_y_se_oculta(cfg):
    s = Service(cfg)
    demo = ui.build_ui(lambda: s)
    rep = next(f for f in demo.fns.values() if len(f.inputs) == 3 and len(f.outputs) == 3)
    hist, report, sin = rep.fn("cuanto cuesta un vuelo a Paris", [], "cid", None)
    assert "Gracias" in hist[-1]["content"] and report["visible"] is False and sin == ""
    assert len(s.reportes) == 1


def test_ejemplos_cargados_al_abrir(cfg):
    s = Service(cfg)
    demo = ui.build_ui(lambda: s)
    load = next(f for f in demo.fns.values() if len(f.inputs) == 0 and len(f.outputs) == ui.N_EJEMPLOS)
    ups = load.fn()
    assert len(ups) == ui.N_EJEMPLOS and all(u["visible"] for u in ups)
    assert ups[0]["value"] == "¿Dónde entrego mis documentos de inscripción?"


def test_panel_de_informacion_oculto_y_con_datos(cfg):
    assert "Calle Veracruz No. 235" in ui._info_md() and "662 336 6626" in ui._info_md()
    demo = ui.build_ui(lambda: Service(cfg))
    toggle = next(f for f in demo.fns.values() if len(f.inputs) == 1 and len(f.outputs) == 3)
    abre = toggle.fn(False)
    assert abre[0]["visible"] is True and abre[1] is True
    assert toggle.fn(True)[0]["visible"] is False
