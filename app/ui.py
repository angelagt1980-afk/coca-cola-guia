"""Interfaz Gradio de GTU GUÍA: chat directo, modo oscuro con la paleta del Grupo Tecnológico Universitario.

Paleta oficial: #FF5100 #FF7D00 (naranjas) · #06096F #046DB4 #234488 (azules) · #6E306F · #363636 #8B8B8B · #F5F5F5 #FFFFFF.
Derivados para el modo oscuro: fondo #0B0E1F y superficies #131838/#1A2050 (azul marino muy oscuro, tono de #06096F).
Contraste: texto #F5F5F5 sobre fondo oscuro (>15:1), burbuja del usuario blanco sobre #234488/#046DB4 (≥5:1),
flecha de envío #06096F sobre naranja (≈7:1). Los enlaces usan un tinte claro de #046DB4 porque el original sobre oscuro no llega a 4.5:1.
"""
from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable

import gradio as gr

from .config import BASE, settings

log = logging.getLogger("campusguia")

ORANGE, ORANGE2 = "#FF5100", "#FF7D00"
NAVY, BLUE, BRAND = "#06096F", "#046DB4", "#234488"
PURPLE, INK, GRAY, SOFT, WHITE = "#6E306F", "#363636", "#8B8B8B", "#F5F5F5", "#FFFFFF"
BG, SURFACE, SURFACE2, LINE, LINK = "#0B0E1F", "#131838", "#1A2050", "rgba(255,255,255,.10)", "#6DB6F0"

SALUDO = "Hola, soy **GTU GUÍA**. Escribe tu duda sobre trámites o servicios del campus y te respondo al instante."
LEGAL = ("GTU GUÍA es una guía de apoyo: confirma los trámites importantes con la oficina responsable. "
         "Tus preguntas se procesan con un servicio de IA de un tercero; no escribas datos personales ni de salud. "
         "En una emergencia sigue los protocolos oficiales del campus.")
INFO_FALLBACK = "**GTU CAMPUS HERMOSILLO**\nGrupo Tecnológico Universitario"
N_EJEMPLOS = 4


def _both(d: dict) -> dict:
    """El tema oscuro se aplica igual en claro y oscuro: si el navegador no activara .dark, nada queda ilegible."""
    return {**d, **{k + "_dark": v for k, v in d.items()}}


THEME = gr.themes.Base(
    font=["Inter", "system-ui", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
    radius_size=gr.themes.sizes.radius_lg,
).set(**_both({
    "body_background_fill": BG, "body_text_color": SOFT, "body_text_color_subdued": GRAY,
    "background_fill_primary": BG, "background_fill_secondary": SURFACE,
    "block_background_fill": "transparent", "block_border_color": "transparent", "block_border_width": "0px",
    "block_shadow": "none", "block_label_text_color": GRAY, "block_title_text_color": SOFT,
    "panel_background_fill": SURFACE, "border_color_primary": "rgba(255,255,255,.10)",
    "input_background_fill": SURFACE, "input_border_color": "rgba(255,255,255,.10)", "input_border_color_focus": ORANGE2,
    "input_placeholder_color": GRAY,
    "button_primary_background_fill": ORANGE, "button_primary_background_fill_hover": ORANGE2,
    "button_primary_text_color": NAVY, "button_primary_border_color": ORANGE,
    "button_secondary_background_fill": SURFACE, "button_secondary_background_fill_hover": SURFACE2,
    "button_secondary_text_color": SOFT, "button_secondary_border_color": "rgba(255,255,255,.10)",
    "link_text_color": LINK,
}))

CSS = f"""
body, .gradio-container {{
  background: radial-gradient(900px 480px at 0% -8%, rgba(35,68,136,.50), transparent 60%),
              radial-gradient(700px 420px at 100% -5%, rgba(255,81,0,.15), transparent 60%), {BG} !important; }}
.gradio-container {{ max-width: 760px !important; margin: 0 auto !important; padding: 0 12px !important; }}
footer {{ display:none !important; }}

#top {{ align-items:center !important; flex-wrap:nowrap !important; gap:.5rem; padding:.9rem 0 .8rem; position:relative;
  border-bottom:1px solid {LINE}; }}
#top::after {{ content:""; position:absolute; left:0; bottom:-1px; width:104px; height:2px;
  background:linear-gradient(90deg,{ORANGE},{ORANGE2}); }}
#brand {{ display:flex; align-items:center; gap:.9rem; }}
#brand img {{ height:44px; width:auto; }}
#brand .t {{ display:flex; flex-direction:column; line-height:1.15; }}
#brand .t b {{ font-size:1.3rem; letter-spacing:.09em; color:{SOFT}; }}
#brand .t b i {{ font-style:normal; color:{ORANGE2}; }}
#brand .t span {{ font-size:.8rem; color:{GRAY}; }}

#info-btn {{ flex:0 0 40px !important; min-width:40px !important; width:40px !important; height:40px; padding:0 !important;
  border-radius:50% !important; background:transparent !important; color:{SOFT} !important;
  border:1px solid rgba(255,255,255,.25) !important; font:italic 700 1.05rem Georgia, serif !important; }}
#info-btn:hover {{ border-color:{ORANGE2} !important; color:{ORANGE2} !important; }}
#info-panel {{ position:fixed; top:74px; right:14px; z-index:100; width:min(92vw,340px); padding:1rem 1.15rem !important;
  background:{SURFACE2} !important; border:1px solid rgba(255,255,255,.14) !important; border-radius:16px;
  box-shadow:0 18px 50px rgba(0,0,0,.6); }}
#info-panel, #info-panel * {{ color:{SOFT}; font-size:.92rem; line-height:1.5; }}
#info-panel a {{ color:{LINK}; }}

#chat {{ border:0 !important; background:transparent !important; }}
#chat [data-testid="user"], #chat .message.user {{ background:linear-gradient(135deg,{BRAND},{BLUE}) !important; color:{WHITE} !important;
  border:0 !important; border-radius:20px 20px 6px 20px !important; }}
#chat [data-testid="user"] *, #chat .message.user * {{ color:{WHITE} !important; }}
#chat [data-testid="bot"], #chat .message.bot {{ background:{SURFACE} !important; color:{SOFT} !important; border:1px solid {LINE} !important;
  border-left:3px solid {ORANGE2} !important; border-radius:6px 20px 20px 20px !important; }}
#chat [data-testid="bot"] *, #chat .message.bot * {{ color:{SOFT}; }}
#chat [data-testid="bot"] strong {{ color:{WHITE}; }}
#chat a {{ color:{LINK} !important; }}

#chips {{ flex-wrap:wrap !important; gap:.5rem !important; }}
.chip {{ flex:0 1 auto !important; min-width:0 !important; border-radius:999px !important; background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.16) !important; color:{SOFT} !important; font-size:.9rem !important; padding:.45rem .95rem !important; }}
.chip:hover {{ border-color:{ORANGE2} !important; background:rgba(255,125,0,.10) !important; }}

#report-row {{ align-items:center !important; gap:.75rem; }}
#report-btn {{ flex:0 0 auto !important; border-radius:999px !important; background:transparent !important; color:{ORANGE2} !important;
  border:1px solid {ORANGE2} !important; font-size:.9rem !important; }}
#report-btn:hover {{ background:rgba(255,125,0,.12) !important; }}
#report-note {{ font-size:.8rem; color:{GRAY}; }}

#msg {{ background:{SURFACE} !important; border:1px solid rgba(255,255,255,.14) !important; border-radius:28px !important; padding:.25rem .4rem .25rem 1rem !important; }}
#msg:focus-within {{ border-color:{ORANGE2} !important; box-shadow:0 0 0 3px rgba(255,125,0,.22); }}
#msg textarea {{ background:transparent !important; border:0 !important; box-shadow:none !important; color:{SOFT} !important; font-size:1.02rem; }}
#msg button {{ background:linear-gradient(135deg,{ORANGE},{ORANGE2}) !important; color:{NAVY} !important; border:0 !important;
  border-radius:50% !important; min-width:42px; min-height:42px; }}
#msg button svg {{ color:{NAVY} !important; fill:{NAVY} !important; stroke:{NAVY} !important; }}

#uso, #legal {{ font-size:.78rem; color:{GRAY}; text-align:center; }}
#uso p, #legal p {{ color:{GRAY}; margin:.15rem 0; }}
button:focus-visible, textarea:focus-visible, a:focus-visible {{ outline:3px solid {ORANGE2} !important; outline-offset:2px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; }} }}
"""

JS = """() => {
  document.documentElement.lang = 'es';
  document.body.classList.add('dark');
  const label = (sel, text) => { const t = setInterval(() => { const e = document.querySelector(sel);
    if (e) { e.setAttribute('aria-label', text); clearInterval(t); } }, 300); setTimeout(() => clearInterval(t), 8000); };
  label('#info-btn', 'Información del campus');
  label('#msg button', 'Enviar pregunta');
}"""

_MD = re.compile(r"([\\`*_{}\[\]<>()#+!|~])")


def esc(s: str) -> str:
    """Escapa caracteres de Markdown/HTML: el contenido del corpus se muestra como texto, nunca como formato."""
    return _MD.sub(r"\\\1", s or "")


def format_reply(d: dict) -> str:
    """Convierte la respuesta del servicio en Markdown seguro."""
    parts = [esc(d.get("respuesta", "")).replace("\n", "  \n")]
    for a in d.get("advertencias", []):
        parts.append(f"**Aviso:** {esc(a)}")
    for f in d.get("fichas", []):
        head = f"**{esc(f['titulo'])}**" + (f" — {esc(f['puesto'])}" if f.get("puesto") else "")
        rows = [("Responsable", f.get("responsable")), ("Ubicación", f.get("ubicacion")), ("Horario", f.get("horario")),
                ("Teléfono", f.get("telefono")), ("Correo", f.get("correo")), ("Web", f.get("web")),
                ("Actualizado", f.get("actualizado"))]
        lines = [f"- **{k}:** {esc(v)}" for k, v in rows if v]
        if f.get("desactualizado"):
            lines.append("- **Aviso:** esta información puede estar desactualizada; confirma con la oficina.")
        parts.append(head + "\n" + "\n".join(lines))
    if d.get("fuentes"):
        src = "; ".join(f"[{s['n']}] {esc(s['titulo'])}" + (f" ({s['actualizado']})" if s.get("actualizado") else "")
                        for s in d["fuentes"])
        parts.append(f"*Fuentes:* {src}")
    return "\n\n".join(parts)


def handle(msg: str, history: list, cid: str, ip: str, service) -> tuple[list, str, str]:
    """Lógica del chat, independiente de Gradio (se prueba sin navegador).

    Devuelve (historial, texto de uso, pregunta sin respuesta). La tercera es "" salvo que no hubiera información.
    """
    history = list(history or [])
    msg = " ".join((msg or "").split())[: settings.max_query_chars]
    if not msg:
        return history, "", ""
    sin = ""
    if not service.quota.rate_ok(ip, cid):
        reply, uso = "Hiciste muchas consultas seguidas. Espera un minuto e inténtalo de nuevo.", ""
    else:
        try:
            d = service.responder(msg, "todos", ip, cid)
            reply = format_reply(d)
            r = d.get("uso", {})
            uso = f"Consultas con IA restantes hoy: {r['consultas']}" if "consultas" in r else ""
            sin = msg if d.get("tipo") == "abstencion" else ""
        except Exception:  # nunca mostrar un error técnico al usuario
            log.exception("error inesperado en el chat")
            reply, uso = "Ocurrió un error. Inténtalo de nuevo en un momento.", ""
    history += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
    return history, uso, sin


def client_ip(request) -> str:
    if request is None:
        return "?"
    xff = request.headers.get("x-forwarded-for", "") if request.headers else ""
    return (xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?"))[:64]


def _info_md() -> str:
    p = BASE / "data" / "info_campus.md"
    return p.read_text("utf-8") if p.exists() else INFO_FALLBACK


def build_ui(get_service: Callable[[], object]) -> gr.Blocks:
    with gr.Blocks(title="GTU GUÍA · Grupo Tecnológico Universitario", analytics_enabled=False) as demo:
        with gr.Row(elem_id="top"):
            gr.HTML('<div id="brand"><img src="/static/logo_dark.png" alt="Grupo Tecnológico Universitario">'
                    '<div class="t"><b>GTU <i>GUÍA</i></b><span>Trámites y servicios del campus</span></div></div>')
            info_btn = gr.Button("i", elem_id="info-btn", scale=0)
        with gr.Column(visible=False, elem_id="info-panel") as info_panel:
            gr.Markdown(_info_md())

        chat = gr.Chatbot(value=[{"role": "assistant", "content": SALUDO}], elem_id="chat", height="56vh",
                          show_label=False, label="Conversación", buttons=[])
        with gr.Row(elem_id="chips") as chips:
            ejemplos = [gr.Button("", elem_classes="chip", visible=False, size="sm") for _ in range(N_EJEMPLOS)]
        with gr.Row(visible=False, elem_id="report-row") as report_row:
            report_btn = gr.Button("Informar que falta esta información", elem_id="report-btn", size="sm", scale=0)
            gr.Markdown("Se envía solo tu pregunta, sin datos personales.", elem_id="report-note")
        msg = gr.Textbox(elem_id="msg", container=False, show_label=False, label="Tu pregunta", lines=1, max_lines=4,
                         placeholder="Escribe tu duda…", max_length=settings.max_query_chars, submit_btn=True,
                         autofocus=True)
        uso = gr.Markdown("", elem_id="uso")
        gr.Markdown(LEGAL, elem_id="legal")

        cid_state = gr.BrowserState(None)  # id anónimo (solo para los cupos de uso); la conversación NO se guarda
        sin_state = gr.State("")
        open_state = gr.State(False)

        def on_send(text, history, cid, request: gr.Request):
            cid = cid or uuid.uuid4().hex
            history, u, sin = handle(text, history, cid, client_ip(request), get_service())
            return (history, "", u, cid, gr.update(visible=False), gr.update(visible=bool(sin)), sin)

        ins, outs = [msg, chat, cid_state], [chat, msg, uso, cid_state, chips, report_row, sin_state]
        msg.submit(on_send, ins, outs, api_name=False, concurrency_limit=8)
        for b in ejemplos:  # el valor del botón es la pregunta modelo
            b.click(on_send, [b, chat, cid_state], outs, api_name=False, concurrency_limit=8)

        def on_report(sin, history, cid, request: gr.Request):
            _ok, texto = get_service().reportar(sin, client_ip(request), cid or "anon")
            history = list(history or []) + [{"role": "assistant", "content": esc(texto)}]
            return history, gr.update(visible=False), ""

        report_btn.click(on_report, [sin_state, chat, cid_state], [chat, report_row, sin_state], api_name=False)

        def on_info(opened):
            return gr.update(visible=not opened), not opened, gr.update(value="✕" if not opened else "i")

        info_btn.click(on_info, [open_state], [info_panel, open_state, info_btn], api_name=False)

        def cargar_ejemplos():  # se ejecuta en cada visita: siempre una conversación nueva y ejemplos actualizados
            ej = get_service().ejemplos(N_EJEMPLOS)
            return [gr.update(value=ej[i], visible=True) if i < len(ej) else gr.update(visible=False)
                    for i in range(N_EJEMPLOS)]

        demo.load(cargar_ejemplos, None, ejemplos, api_name=False)
        demo.queue(max_size=32)
    return demo
