"""Control de consumo y fallos de auditoría en el límite del chasis."""
from __future__ import annotations

import pytest

from chasis import auditoria, cli, procedencia
from chasis.agente import Agente
from chasis.config import Ajustes
from chasis.ia import ClienteIA, Respuesta
from chasis.medalla import cargar


class ClienteFalso:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0

    def conversar(self, mensajes, herramientas=None):
        self.llamadas += 1
        return self.respuestas.pop(0)


def respuesta(texto='', *, herramientas=False, entrada=0, salida=0, uso=True):
    llamadas = ([{'id': '1', 'function': {'name': 'inexistente', 'arguments': '{}'}}]
                if herramientas else [])
    return Respuesta(texto, llamadas, 'falso', entrada, salida, uso)


def agente(cliente, limite=None):
    return Agente(cargar('documentos'), ajustes=Ajustes(max_tokens_turno=limite),
                  cliente=cliente)


def test_presupuesto_acumulado_detiene_llamadas_y_herramientas():
    cliente = ClienteFalso(respuesta(herramientas=True, entrada=30, salida=10),
                           respuesta(herramientas=True, entrada=40, salida=20))
    turno = agente(cliente, 100).ejecutar('encargo')
    assert cliente.llamadas == 2
    assert len(turno.pasos) == 1
    assert turno.tokens_entrada + turno.tokens_salida == 100
    assert turno.incompleto
    assert 'límite de tokens' in turno.respuesta


def test_consumo_desconocido_detiene_las_herramientas():
    cliente = ClienteFalso(respuesta(herramientas=True, uso=False))
    turno = agente(cliente, 100).ejecutar('encargo')
    assert cliente.llamadas == 1 and not turno.pasos
    assert turno.incompleto
    assert 'no informó el consumo' in turno.respuesta


def test_respuesta_final_avisa_si_no_hay_uso_o_si_supera_el_umbral():
    sin_uso = agente(ClienteFalso(respuesta('Terminé', uso=False)), 100).ejecutar('x')
    superado = agente(ClienteFalso(respuesta('Terminé', entrada=80, salida=30)), 100).ejecutar('x')
    assert not sin_uso.incompleto and 'no informó el consumo' in sin_uso.respuesta
    assert not superado.incompleto and 'superó el límite' in superado.respuesta


def test_presupuesto_no_configurado_conserva_el_flujo_anterior():
    cliente = ClienteFalso(respuesta(herramientas=True, uso=False), respuesta('Terminé', uso=False))
    turno = agente(cliente).ejecutar('x')
    assert cliente.llamadas == 2 and len(turno.pasos) == 1
    assert turno.respuesta == 'Terminé' and not turno.incompleto


def test_cierre_forzado_cuenta_consumo_y_avisa_si_supera_umbral():
    cliente = ClienteFalso(respuesta(herramientas=True, entrada=40, salida=10),
                           respuesta('Cierre', entrada=40, salida=20))
    turno = agente(cliente, 100).ejecutar('x', max_pasos=1)
    assert cliente.llamadas == 2
    assert not turno.incompleto and 'superó el límite' in turno.respuesta


def test_fallo_auditoria_visible_y_no_limpio(monkeypatch):
    def fallo(_):
        raise RuntimeError('detalle interno')
    monkeypatch.setattr(auditoria, 'auditar', fallo)
    turno = agente(ClienteFalso(respuesta('Resultado'))).ejecutar('x')
    assert turno.auditoria_error and not turno.limpio
    assert 'auditoría no pudo completarse' in turno.respuesta
    assert 'detalle interno' not in turno.respuesta


def test_fallo_procedencia_se_distingue_de_auditoria(monkeypatch):
    def fallo(*args):
        raise RuntimeError('detalle interno')
    monkeypatch.setattr(procedencia, 'etiquetar', fallo)
    turno = agente(ClienteFalso(respuesta('Resultado'))).ejecutar('x')
    assert turno.limpio and not turno.auditoria_error
    assert 'procedencia no pudo calcularse' in turno.procedencia['error']
    assert 'no se pudo calcular la procedencia' in turno.respuesta


@pytest.mark.parametrize('valor', ['0', '-1', 'abc', ''])
def test_presupuesto_invalido_falla_con_mensaje(monkeypatch, capsys, valor):
    monkeypatch.setenv('ROKUSHO_MAX_TOKENS_TURNO', valor)
    assert cli.main(['ver', '--medalla', 'documentos']) == 2
    assert 'ROKUSHO_MAX_TOKENS_TURNO' in capsys.readouterr().err


def test_presupuesto_se_lee_del_entorno(monkeypatch):
    monkeypatch.setenv('ROKUSHO_MAX_TOKENS_TURNO', '100')
    assert Ajustes.desde_entorno().max_tokens_turno == 100


def test_cli_devuelve_error_si_el_encargo_queda_incompleto(monkeypatch, capsys):
    ag = agente(ClienteFalso(respuesta(herramientas=True, entrada=100)), 100)
    monkeypatch.setattr(cli, 'Agente', lambda *args: ag)
    assert cli.main(['trabajar', '--medalla', 'documentos', '--encargo', 'x']) == 4
    assert 'incompleto' in capsys.readouterr().out


def test_proveedor_identifica_consumo_ausente_o_incompleto():
    cliente = object.__new__(ClienteIA)
    cliente.ajustes = Ajustes()
    base = {'choices': [{'message': {'content': 'ok'}}]}
    assert not cliente._leer(base).uso_disponible
    assert not cliente._leer({**base, 'usage': {'prompt_tokens': 10}}).uso_disponible
    medido = cliente._leer({**base, 'usage': {'prompt_tokens': 10, 'completion_tokens': 2}})
    assert medido.uso_disponible and (medido.tokens_entrada, medido.tokens_salida) == (10, 2)
    texto = cliente._leer({**base, 'usage': {'prompt_tokens': '10', 'completion_tokens': '2'}})
    assert texto.uso_disponible and (texto.tokens_entrada, texto.tokens_salida) == (10, 2)
