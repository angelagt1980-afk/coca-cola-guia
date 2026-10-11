from app.corpus import parse_corpus

OK = """### a-uno
TITULO: Uno
TAGS: x, y
ACTUALIZADO: 2026-01-01
--
Texto.

### a-dos
TITULO: Dos
CORREO: mal-correo
AUDIENCIA: alumnos
--
Texto 2.
"""


def test_parse_valido_y_avisos():
    entries, problems = parse_corpus(OK)
    assert [e.id for e in entries] == ["a-uno", "a-dos"]
    assert entries[0].tags == ["x", "y"]
    msgs = " ".join(str(p) for p in problems)
    assert "CORREO" in msgs and "AUDIENCIA" in msgs and "TAGS" in msgs
    assert entries[1].audiencia == ["todos"]


def test_errores_omiten_entrada():
    entries, problems = parse_corpus("### sin-titulo\nTAGS: a\n--\ntexto\n### repetido\nTITULO: R\n--\nx\n### repetido\nTITULO: R2\n--\ny\n")
    assert [e.id for e in entries] == ["repetido"]
    assert sum(p.level == "error" for p in problems) == 2


def test_corpus_vacio_es_error():
    _, problems = parse_corpus("solo comentarios")
    assert any(p.level == "error" for p in problems)


def test_corpus_real_sin_errores():
    from app.config import BASE
    entries, problems = parse_corpus((BASE / "data" / "corpus.txt").read_text("utf-8"))
    assert entries and not [p for p in problems if p.level == "error"]
