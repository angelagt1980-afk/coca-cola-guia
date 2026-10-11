from app import llm
from app.service import Service

Q_LLM = "¿Cómo entrego mis documentos de inscripción en el edificio?"


def fake_llm(texto="Entrega tus documentos en Servicios Escolares [servicios-escolares].", tin=700, tout=60, calls=None):
    def f(s, system, user, max_tokens):
        if calls is not None:
            calls.append((system, user, max_tokens))
        return texto, tin, tout
    return f


def con_llm(cfg, **kw):
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    return Service(cfg, llm_fn=fake_llm(**kw))


def test_emergencia_deriva_sin_tokens(cfg):
    r = Service(cfg).responder("hay un incendio en el edificio", "todos", "ip", "c")
    assert r["tipo"] == "derivacion" and "911" in r["respuesta"] and r["fichas"] == []


def test_salud_deriva(cfg):
    r = Service(cfg).responder("que medicamento me tomo para el dolor de cabeza", "todos", "ip", "c")
    assert r["tipo"] == "derivacion" and "médica" in r["respuesta"]


def test_abstencion_sin_evidencia_no_llama_llm(cfg):
    calls = []
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    s = Service(cfg, llm_fn=fake_llm(calls=calls))
    r = s.responder("cuanto cuesta un boleto de avion a Paris", "todos", "ip", "c")
    assert r["tipo"] == "abstencion" and not calls
    assert s.gaps and "boleto" in s.gaps[0]["pregunta"]


def test_sin_llm_responde_directo_con_ficha(cfg):
    r = Service(cfg).responder("horario biblioteca", "todos", "ip", "c")
    assert r["tipo"] == "directa"
    assert r["fichas"][0]["id"] == "biblioteca" and r["fichas"][0]["horario"]


def test_llm_cita_validada_y_tokens_contados(cfg):
    calls = []
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    s = Service(cfg, llm_fn=fake_llm(calls=calls))
    r = s.responder(Q_LLM, "estudiante", "ip", "c")
    assert r["tipo"] == "llm" and r["verificacion"] == "verificada"
    assert "[1]" in r["respuesta"] and r["fuentes"][0]["id"] == "servicios-escolares"
    assert r["uso"]["tokens_consulta"] == 760
    _system, user, mx = calls[0]
    assert mx == cfg.max_output_tokens and len(user) < cfg.max_context_chars + 600
    assert "@" not in user and "662 000" not in user  # correos y teléfonos nunca se envían al LLM


def test_cita_inventada_se_descarta(cfg):
    s = con_llm(cfg, texto="Ve a la oficina [no-existe].")
    r = s.responder(Q_LLM, "estudiante", "ip", "c")
    assert r["verificacion"] == "no_verificada" and "[no-existe]" not in r["respuesta"]


def test_cache_evita_segunda_llamada(cfg):
    calls = []
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    s = Service(cfg, llm_fn=fake_llm(calls=calls))
    q = Q_LLM
    s.responder(q, "estudiante", "ip", "c")
    r2 = s.responder("Como entrego mis documentos de inscripcion en el edificio", "estudiante", "ip", "c")
    assert len(calls) == 1 and r2.get("desde_cache") and r2["uso"]["tokens_consulta"] == 0


def test_limite_diario_degrada_a_ficha(cfg):
    cfg.user_queries_day = 1
    s = con_llm(cfg)
    s.responder(Q_LLM, "estudiante", "ip", "c")
    r = s.responder("como solicito una beca en el edificio", "estudiante", "ip", "c")
    assert r["tipo"] == "directa" and "límite" in " ".join(r["advertencias"])


def test_fallo_llm_degrada(cfg):
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"

    def boom(*a, **k):
        raise llm.LLMError("timeout")
    r = Service(cfg, llm_fn=boom).responder(Q_LLM, "todos", "ip", "c")
    assert r["tipo"] == "directa" and r["fichas"]


def test_aviso_de_vigencia(cfg):
    r = Service(cfg).responder("captura de calificaciones", "profesor", "ip", "c")
    assert any("actualizó hace" in a for a in r["advertencias"])


def test_consulta_clara_va_directa_aun_con_llm_y_cuesta_0_tokens(cfg):
    calls = []
    cfg.llm_provider, cfg.llm_api_key = "anthropic", "x"
    s = Service(cfg, llm_fn=fake_llm(calls=calls))
    r = s.responder("horario biblioteca", "todos", "ip", "c")
    assert r["tipo"] == "directa" and not calls and r["uso"]["tokens_consulta"] == 0


def test_contexto_respeta_presupuesto(cfg):
    cfg.max_context_chars = 600
    s = Service(cfg)
    hits = s.index.search("inscripcion becas biblioteca wifi", "todos", 3)
    assert len(s._context(hits)) <= 600
