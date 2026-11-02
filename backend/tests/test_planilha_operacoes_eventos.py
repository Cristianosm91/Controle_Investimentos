import io
from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from app.dominio import EVENTOS_PLANILHA_CODIGOS, EVENTOS_PLANILHA_NAO_SUPORTADOS
from app.services import extrato_b3, modelos


def _linha(evento: str, quantidade: str, preco: str):
    return extrato_b3._linha_planilha_operacoes(
        12,
        date(2026, 1, 5),
        {"ticker": "PETR4", "evento": evento, "moeda": "BRL"},
        Decimal(quantidade),
        Decimal(preco),
        "XP",
    )


def test_siglas_operacionais_normalizam_para_eventos_do_dominio():
    casos = [
        (" c ", "100", "10", "C", Decimal("100"), False),
        ("v", "10", "11", "V", Decimal("-10"), False),
        ("ipo", "10", "5", "C", Decimal("10"), False),
        ("sub", "10", "5", "C", Decimal("10"), False),
        ("bn", "5", "0", "BONIFICACAO", Decimal("5"), False),
        ("AM", "10", "-0.5", "AMORTIZACAO", Decimal("10"), False),
        ("DT", "2", "10", "C", Decimal("2"), True),
        ("DT", "-2", "10", "V", Decimal("-2"), True),
        ("DESDOBRAMENTO", "5", "0", "DESDOBRAMENTO", Decimal("5"), False),
        ("GRUPAMENTO", "-5", "0", "DESDOBRAMENTO", Decimal("-5"), False),
        ("TC", "-10", "10", "TRANSFERENCIA", Decimal("-10"), False),
        ("AT", "10", "10", "TRANSFERENCIA", Decimal("10"), False),
        ("V.SUB", "3", "2", "VENDA_SUBSCRICAO", Decimal("-3"), False),
        ("CISAO", "10", "-1", "CISAO", Decimal("10"), False),
    ]

    for codigo, quantidade, preco, evento, sinal, daytrade in casos:
        linha = _linha(codigo, quantidade, preco)
        assert linha.tipo == "OPERACAO", linha.motivo
        assert linha.evento == evento
        assert linha.quantidade == sinal
        assert linha.daytrade is daytrade
        assert linha.evento_original == codigo.strip().upper()


def test_sigla_desconhecida_e_codigo_valido_nao_suportado_identificam_linha():
    desconhecido = _linha("XX", "1", "10")
    assert desconhecido.tipo == "IGNORADA"
    assert "Linha 12" in desconhecido.motivo
    assert "'XX'" in desconhecido.motivo
    assert "não reconhecido" in desconhecido.motivo

    nao_suportado = _linha("EX.OPC", "1", "10")
    assert nao_suportado.tipo == "IGNORADA"
    assert "Linha 12" in nao_suportado.motivo
    assert "'EX.OPC'" in nao_suportado.motivo
    assert "não suportado" in nao_suportado.motivo


@pytest.mark.parametrize("codigo", EVENTOS_PLANILHA_NAO_SUPORTADOS)
def test_codigos_documentados_fora_do_modelo_rejeitam_com_motivo(codigo: str):
    linha = _linha(codigo, "1", "10")

    assert linha.tipo == "IGNORADA"
    assert "Linha 12" in linha.motivo
    assert f"'{codigo}'" in linha.motivo
    assert "não suportado" in linha.motivo


def test_validacao_exige_sinais_e_campos_compativeis_com_evento():
    amortizacao_invalida = _linha("AM", "0", "-50")
    assert amortizacao_invalida.tipo == "IGNORADA"
    assert "AM" in amortizacao_invalida.motivo
    assert "quantidade/preço" in amortizacao_invalida.motivo

    bonificacao_invalida = _linha("BN", "2", "1")
    assert bonificacao_invalida.tipo == "IGNORADA"
    assert "BN" in bonificacao_invalida.motivo

    desdobramento_invalido = _linha("DESDOBRAMENTO", "2", "5")
    assert desdobramento_invalido.tipo == "IGNORADA"
    assert "DESDOBRAMENTO" in desdobramento_invalido.motivo

    taxa_negativa = extrato_b3._linha_planilha_operacoes(
        12,
        date(2026, 1, 5),
        {"ticker": "PETR4", "evento": "C", "moeda": "BRL", "taxas": "-1"},
        Decimal("1"),
        Decimal("10"),
        "XP",
    )
    assert taxa_negativa.tipo == "IGNORADA"
    assert "taxas e IRRF não podem ser negativos" in taxa_negativa.motivo


def test_modelo_explica_eventos_e_apresenta_a_lista_suportada():
    _, conteudo = modelos.gerar("planilha-operacoes")
    livro = openpyxl.load_workbook(io.BytesIO(conteudo))
    instrucoes = "\n".join(str(c.value or "") for linha in livro["Instruções"] for c in linha)

    assert all(codigo in instrucoes for codigo in EVENTOS_PLANILHA_CODIGOS)
    assert "Modelo personalizado" in instrucoes
    assert "Proventos" in instrucoes
    assert "não são suportados" in instrucoes
