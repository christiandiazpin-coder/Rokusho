"""Pruebas de la pieza «memoria».

Lo que se protege aquí: que un dato guardado conserve su procedencia, que
actualizarlo no borre la fuente, y que la memoria no crezca sin límite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chasis.pieza import cargar

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture()
def f(tmp_path):
    pieza = cargar("memoria", raiz=RAIZ / "piezas")
    pieza.configurar(tmp_path)
    return {h.nombre: h.funcion for h in pieza.herramientas}


def test_memoria_vacia(f):
    assert "vacía" in f["listar_memoria"]()
    assert "vacía" in f["recuperar"]("cualquier cosa")


def test_guardar_y_recuperar(f):
    f["recordar"]("cliente", "Comercial Valparaíso Ltda.", "contrato.txt línea 3")
    r = f["recuperar"]("cliente")
    assert "Comercial Valparaíso" in r
    assert "contrato.txt línea 3" in r


def test_guardar_sin_fuente_avisa(f):
    """Un dato sin procedencia no se puede verificar: hay que avisarlo."""
    r = f["recordar"]("contacto", "El gerente se llama Juan")
    assert "AVISO" in r and "fuente" in r


def test_actualizar_conserva_fuente_anterior(f):
    f["recordar"]("moneda", "Pesos chilenos", "deducido de SpA/Ltda.")
    r = f["recordar"]("moneda", "Pesos chilenos confirmados")
    assert "actualizada" in r
    # La fuente no se pierde al actualizar sin dar una nueva.
    assert "deducido de SpA/Ltda." in f["recuperar"]("moneda")


def test_actualizar_con_fuente_nueva_la_reemplaza(f):
    f["recordar"]("moneda", "Pesos", "deducido")
    f["recordar"]("moneda", "Pesos", "correo del cliente")
    r = f["recuperar"]("moneda")
    assert "correo del cliente" in r


def test_clave_repetida_no_duplica(f):
    for i in range(5):
        f["recordar"]("clave", f"version {i}")
    assert f["listar_memoria"]().count("clave") == 1


def test_clave_vacia_falla(f):
    assert "ERROR" in f["recordar"]("", "contenido")
    assert "ERROR" in f["recordar"]("   ", "contenido")


def test_contenido_vacio_falla(f):
    assert "ERROR" in f["recordar"]("clave", "   ")


def test_contenido_demasiado_largo_falla(f):
    assert "ERROR" in f["recordar"]("clave", "x" * 5000)


def test_clave_con_saltos_no_rompe_el_archivo(f):
    f["recordar"]("clave\n## inyectada", "contenido")
    r = f["listar_memoria"]()
    assert "## inyectada" not in r
    assert f["olvidar"]("clave ## inyectada").startswith("Borrada")


def test_no_encontrado_no_inventa(f):
    f["recordar"]("cliente", "Empresa X")
    r = f["recuperar"]("proveedor")
    assert "No hay nada" in r
    assert "no inventarlo" in r


def test_olvidar_borra(f):
    f["recordar"]("temporal", "algo")
    assert "Borrada" in f["olvidar"]("temporal")
    assert "vacía" in f["listar_memoria"]()


def test_olvidar_inexistente_avisa(f):
    f["recordar"]("cliente", "X")
    r = f["olvidar"]("proveedor")
    assert "ERROR" in r


def test_olvidar_sugiere_parecidas(f):
    f["recordar"]("moneda", "CLP")
    r = f["olvidar"]("mon")
    assert "ERROR" in r


def test_la_memoria_sobrevive_entre_sesiones(tmp_path):
    """Se vuelve a cargar la pieza y el dato sigue ahí: eso es «entre sesiones»."""
    pieza1 = cargar("memoria", raiz=RAIZ / "piezas")
    pieza1.configurar(tmp_path)
    f1 = {h.nombre: h.funcion for h in pieza1.herramientas}
    f1["recordar"]("cliente", "Empresa Persistente", "contrato")

    pieza2 = cargar("memoria", raiz=RAIZ / "piezas")
    pieza2.configurar(tmp_path)
    f2 = {h.nombre: h.funcion for h in pieza2.herramientas}
    assert "Empresa Persistente" in f2["recuperar"]("cliente")


def test_el_archivo_es_legible_por_una_persona(f, tmp_path):
    f["recordar"]("cliente", "Empresa X", "contrato.txt")
    archivo = tmp_path / "memoria.md"
    assert archivo.is_file()
    texto = archivo.read_text(encoding="utf-8")
    assert "Empresa X" in texto
    assert "contrato.txt" in texto
    assert texto.startswith("# Memoria")
