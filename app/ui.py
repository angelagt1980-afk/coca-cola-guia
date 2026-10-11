"""Interfaz Gradio (chat minimalista) con la marca del Grupo Tecnológico Universitario.

Paleta oficial: #FF5100 #FF7D00 (naranjas) · #06096F #046DB4 #234488 (azules) · #6E306F · #363636 #8B8B8B · #F5F5F5 #FFFFFF.
Accesibilidad: el texto y los botones usan azul #234488 sobre blanco (contraste ≈ 9:1). Los naranjas se reservan
para acentos decorativos porque #FF7D00 sobre blanco NO alcanza 4.5:1.
"""
from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable

import gradio as gr

from .config import settings

log = logging.getLogger("campusguia")

ORANGE, ORANGE2 = "#FF5100", "#FF7D00"
NAVY, BLUE, BRAND = "#06096F", "#046DB4", "#234488"
PURPLE, INK, GRAY, SOFT, WHITE = "#6E306F", "#363636", "#8B8B8B", "#F5F5F5", "#FFFFFF"

SALUDO = ("Hola, soy **CampusGuía**. Pregúntame por trámites y servicios del campus: "
          "dónde queda una oficina, qué documentos llevar, horarios o cómo contactar a alguien.")
EJEMPLOS = ["¿Dónde entrego mis documentos de inscripción?", "Horario de la biblioteca",
            "¿Cómo solicito una beca?", "No puedo conectarme al Wi-Fi"]
PERFILES = [("Estudiante", "estudiante"), ("Profesor", "profesor"), ("Otro / prefiero no decir", "todos")]

AVISO = ("CampusGuía es una guía de apoyo: para trámites importantes confirma con la oficina responsable. "
         "Tus preguntas se procesan con un servicio de IA de un tercero; no escribas datos personales ni de salud. "
         "En una emergencia sigue los protocolos oficiales del campus.")

THEME = gr.themes.Base(
    font=["system-ui", "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"],
    radius_size=gr.themes.sizes.radius_md,
).set(
    body_background_fill=WHITE, body_background_fill_dark=WHITE,
    body_text_color=INK, body_text_color_dark=INK,
    body_text_color_subdued=GRAY, body_text_color_subdued_dark="#5f5f5f",
    background_fill_primary=WHITE, background_fill_primary_dark=WHITE,
    background_fill_secondary=SOFT, background_fill_secondary_dark=SOFT,
    block_background_fill=WHITE, block_background_fill_dark=WHITE,
    block_border_color="#e1e1e1", block_border_color_dark="#e1e1e1",
    block_label_text_color=INK, block_label_text_color_dark=INK,
    input_background_fill=WHITE, input_background_fill_dark=WHITE,
    input_border_color="#c9c9c9", input_border_color_dark="#c9c9c9",
    input_border_color_focus=BRAND, input_border_color_focus_dark=BRAND,
    button_primary_background_fill=BRAND, button_primary_background_fill_dark=BRAND,
    button_primary_background_fill_hover=NAVY, button_primary_background_fill_hover_dark=NAVY,
    button_primary_text_color=WHITE, button_primary_text_color_dark=WHITE,
    button_primary_border_color=BRAND, button_primary_border_color_dark=BRAND,
    button_secondary_background_fill=WHITE, button_secondary_background_fill_dark=WHITE,
    button_secondary_background_fill_hover=SOFT, button_secondary_background_fill_hover_dark=SOFT,
    button_secondary_text_color=BRAND, button_secondary_text_color_dark=BRAND,
    button_secondary_border_color=BRAND, button_secondary_border_color_dark=BRAND,
    link_text_color=BLUE, link_text_color_dark=BLUE,
)

CSS = f"""
.gradio-container {{ max-width: 860px !important; margin: 0 auto !important; }}
#gtu-header {{ display:flex; align-items:center; gap:1rem; padding:.75rem 0 .9rem;
  background:linear-gradient(90deg,{ORANGE},{ORANGE2}) bottom/100% 4px no-repeat; }}
#gtu-header img {{ height:60px; width:auto; }}
#gtu-header p {{ margin:0; color:{INK}; font-size:1.05rem; }}
#gtu-header p b {{ color:{BRAND}; }}
#aviso {{ font-size:.9rem; color:#5a5a5a; border-left:4px solid {ORANGE2}; padding:.1rem .75rem; margin:.5rem 0; }}
#chat [data-testid="user"], #chat .message.user {{ background:{BRAND} !important; color:{WHITE} !important; border:0 !important; }}
#chat [data-testid="user"] *, #chat .message.user * {{ color:{WHITE} !important; }}
#chat [data-testid="bot"], #chat .message.bot {{ background:{SOFT} !important; color:{INK} !important;
  border:0 !important; border-left:4px solid {ORANGE2} !important; }}
#chat [data-testid="bot"] strong {{ color:{BRAND}; }}
#chat a {{ color:{BLUE}; }}
#uso {{ font-size:.85rem; color:#5a5a5a; text-align:right; }}
button:focus-visible, textarea:focus-visible, input:focus-visible, select:focus-visible {{ outline:3px solid {BRAND} !important; outline-offset:2px; }}
footer {{ visibility:hidden; height:0; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; }} }}
"""

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


def handle(msg: str, history: list, perfil: str, cid: str, ip: str, service) -> tuple[list, str]:
    """Lógica del chat, independiente de Gradio (se prueba sin navegador). Devuelve (historial, texto de uso)."""
    history = list(history or [])
    msg = " ".join((msg or "").split())[: settings.max_query_chars]
    if not msg:
        return history, ""
    if not service.quota.rate_ok(ip, cid):
        reply, uso = "Hiciste muchas consultas seguidas. Espera un minuto e inténtalo de nuevo.", ""
    else:
        try:
            d = service.responder(msg, perfil, ip, cid)
            reply = format_reply(d)
            r = d.get("uso", {})
            uso = f"Consultas con IA restantes hoy: {r['consultas']}" if "consultas" in r else ""
        except Exception:  # nunca mostrar un error técnico al usuario
            log.exception("error inesperado en el chat")
            reply, uso = "Ocurrió un error. Inténtalo de nuevo en un momento.", ""
    history += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
    return history, uso


def build_ui(get_service: Callable[[], object]) -> gr.Blocks:
    with gr.Blocks(title="CampusGuía · Grupo Tecnológico Universitario", analytics_enabled=False) as demo:
        gr.HTML('<div id="gtu-header"><img src="/static/logo.png" alt="Grupo Tecnológico Universitario">'
                "<p><b>CampusGuía</b><br>Guía de trámites y servicios del campus</p></div>")
        gr.Markdown(AVISO, elem_id="aviso")
        chat = gr.Chatbot(value=[{"role": "assistant", "content": SALUDO}], elem_id="chat", height=440,
                          label="Conversación", show_label=False)
        with gr.Row(equal_height=True):
            perfil = gr.Dropdown(PERFILES, value="todos", label="Soy", scale=1, min_width=170, interactive=True)
            msg = gr.Textbox(label="Tu pregunta", placeholder="Escribe tu pregunta y presiona Enter",
                             max_lines=3, scale=4, max_length=settings.max_query_chars)
        with gr.Row():
            send = gr.Button("Preguntar", variant="primary", scale=2)
            clear = gr.Button("Nueva conversación", variant="secondary", scale=1)
        uso = gr.Markdown("", elem_id="uso")
        gr.Examples(EJEMPLOS, inputs=msg, label="Ejemplos de preguntas")
        cid_state = gr.BrowserState(None)  # id anónimo persistente en el navegador (para los cupos de uso)

        def on_send(text, history, perfil_v, cid, request: gr.Request):
            cid = cid or uuid.uuid4().hex
            headers = request.headers if request else {}
            xff = headers.get("x-forwarded-for", "") if headers else ""
            ip = xff.split(",")[0].strip() if xff else (request.client.host if request and request.client else "?")
            history, u = handle(text, history, perfil_v, cid, ip[:64], get_service())
            return history, "", u, cid

        ins, outs = [msg, chat, perfil, cid_state], [chat, msg, uso, cid_state]
        msg.submit(on_send, ins, outs, api_name=False, concurrency_limit=8)
        send.click(on_send, ins, outs, api_name=False, concurrency_limit=8)
        clear.click(lambda: ([{"role": "assistant", "content": SALUDO}], "", ""), None, [chat, msg, uso], api_name=False)

        def on_like(data: gr.LikeData):
            get_service().metrics["util_si" if data.liked else "util_no"] += 1
        chat.like(on_like, None, None, api_name=False)
        demo.queue(max_size=32)
    return demo
