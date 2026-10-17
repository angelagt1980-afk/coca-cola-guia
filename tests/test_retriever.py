import pytest

from app.service import Service


@pytest.fixture
def idx(cfg):
    return Service(cfg).index


@pytest.mark.parametrize("q,esperado", [
    ("¿Dónde entrego mi documentación de contratación?", "recursos-humanos"),
    ("necesito mi historial o constancia", "recursos-humanos"),
    ("como pido un beneficio o beca", "beneficios-prestaciones"),
    ("contraseña del wifi", "soporte-ti"),
    ("prestamo de manuales", "centro-capacitacion"),
    ("captura de indicadores de calidad", "control-calidad"),
    ("hay elevador", "salud-ocupacional"),
])
def test_top1(idx, q, esperado):
    assert idx.search(q, "todos")[0].entry.id == esperado


def test_perfil_prioriza_audiencia(idx):
    prov = idx.search("alta contratacion", "proveedor")
    assert prov[0].entry.id == "alta-proveedores"


def test_sin_terminos_no_devuelve_nada(idx):
    assert idx.search("que de la el", "todos") == []


def test_fuera_de_alcance_baja_relevancia(cfg):
    s = Service(cfg)
    hits = s.index.search("cuanto cuesta un boleto de avion a Paris", "todos")
    assert not s._relevant(hits)
