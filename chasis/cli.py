#!/usr/bin/env python3
"""Rokusho: chasis modular de agentes.

Uso:
    python -m chasis.cli medallas
    python -m chasis.cli piezas
    python -m chasis.cli ver --medalla documentos --piezas archivos
    python -m chasis.cli trabajar --medalla documentos --piezas archivos \
        --carpeta ./ejemplos/cliente --encargo "Resume el contrato y dime los plazos"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .agente import Agente, ErrorAgente
from .ia import ErrorProveedor
from .medalla import MedallaInvalida, disponibles as medallas_disponibles
from .medalla import cargar as cargar_medalla
from .pieza import PiezaInvalida, disponibles as piezas_disponibles
from .pieza import cargar_varias


def _color(texto: str, codigo: str) -> str:
    return f"\033[{codigo}m{texto}\033[0m" if sys.stdout.isatty() else texto


def cmd_medallas(args: argparse.Namespace) -> int:
    nombres = medallas_disponibles()
    if not nombres:
        print("No hay medallas instaladas.")
        return 1
    print(f"Medallas disponibles ({len(nombres)}):\n")
    for nombre in nombres:
        try:
            m = cargar_medalla(nombre)
        except MedallaInvalida as e:
            print(f"  {_color(nombre, '31')}  INVÁLIDA: {e}")
            continue
        print(f"  {_color(nombre, '36')}  v{m.version}")
        print(f"      {m.descripcion}")
        print(f"      {len(m.reglas)} reglas, {len(m.prohibido)} prohibiciones")
    return 0


def cmd_piezas(args: argparse.Namespace) -> int:
    nombres = piezas_disponibles()
    if not nombres:
        print("No hay piezas instaladas.")
        return 1
    print(f"Piezas disponibles ({len(nombres)}):\n")
    for nombre in nombres:
        try:
            from .pieza import cargar
            p = cargar(nombre)
        except PiezaInvalida as e:
            print(f"  {_color(nombre, '31')}  INVÁLIDA: {e}")
            continue
        print(f"  {_color(nombre, '32')}  v{p.version}")
        print(f"      {p.descripcion}")
        for h in p.herramientas:
            print(f"      - {h.nombre}({', '.join(h.parametros)})")
    return 0


def cmd_ver(args: argparse.Namespace) -> int:
    try:
        medalla = cargar_medalla(args.medalla)
        piezas = cargar_varias(args.piezas or [])
    except (MedallaInvalida, PiezaInvalida) as e:
        print(_color(f"Error: {e}", "31"), file=sys.stderr)
        return 2

    agente = Agente(medalla, piezas)
    print(agente.sistema())
    return 0


def cmd_trabajar(args: argparse.Namespace) -> int:
    try:
        medalla = cargar_medalla(args.medalla)
        piezas = cargar_varias(args.piezas or [])
    except (MedallaInvalida, PiezaInvalida) as e:
        print(_color(f"Error al ensamblar: {e}", "31"), file=sys.stderr)
        return 2

    if args.carpeta:
        carpeta = Path(args.carpeta).expanduser().resolve()
        if not carpeta.is_dir():
            print(_color(f"Error: la carpeta «{carpeta}» no existe.", "31"), file=sys.stderr)
            return 2
        for pieza in piezas:
            # Se usa el gancho del módulo ya importado por la pieza. Reimportar
            # el archivo crearía otra instancia con sus propias globales, y la
            # carpeta se fijaría en la copia que nadie usa.
            if pieza.configurar is not None:
                pieza.configurar(carpeta)

    agente = Agente(medalla, piezas)
    print(_color(f"Medalla: {medalla.nombre}   Piezas: {', '.join(p.nombre for p in piezas) or '(ninguna)'}", "36"))
    print(_color(f"Modelo: {agente.ajustes.modelo}", "90"))
    print()

    try:
        turno = agente.ejecutar(args.encargo)
    except ErrorProveedor as e:
        print(_color(f"Error del proveedor: {e}", "31"), file=sys.stderr)
        return 3
    except ErrorAgente as e:
        print(_color(f"Error del agente: {e}", "31"), file=sys.stderr)
        return 4

    if turno.pasos:
        print(_color("Herramientas usadas:", "90"))
        for p in turno.pasos:
            resumen = p.resultado.splitlines()[0][:100] if p.resultado else "(sin salida)"
            print(_color(f"  {p.numero}. {p.herramienta} → {resumen}", "90"))
        print()

    print(turno.respuesta or _color("(el agente no devolvió texto)", "33"))
    print()
    print(_color(
        f"— modelo: {turno.modelo} · tokens: {turno.tokens_entrada} entrada / "
        f"{turno.tokens_salida} salida · pasos: {len(turno.pasos)}", "90"))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="rokusho",
        description="Chasis modular de agentes: le pones una medalla y cambia de oficio.")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("medallas", help="Lista las medallas instaladas").set_defaults(func=cmd_medallas)
    sub.add_parser("piezas", help="Lista las piezas instaladas").set_defaults(func=cmd_piezas)

    v = sub.add_parser("ver", help="Muestra el prompt de sistema que se armaría")
    v.add_argument("--medalla", required=True)
    v.add_argument("--piezas", nargs="*", default=[])
    v.set_defaults(func=cmd_ver)

    t = sub.add_parser("trabajar", help="Le da un encargo al agente")
    t.add_argument("--medalla", required=True)
    t.add_argument("--piezas", nargs="*", default=[])
    t.add_argument("--carpeta", help="Espacio de trabajo del cliente (solo lectura)")
    t.add_argument("--encargo", required=True)
    t.set_defaults(func=cmd_trabajar)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
