"""Parâmetros de cálculo editáveis na tela de Configurações (tabela `parametro`, chave → texto)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Parametro


@dataclass
class Parametros:
    # A partir desta data o saldo do caixa considera compras, vendas e proventos; vazio = só movimentações.
    caixa_data_inicio: date | None = None
    # Soma o saldo em caixa ao patrimônio do Portfólio.
    caixa_no_portfolio: bool = False
    # Primeiro ano apurado; operações anteriores só formam posição/preço médio. Vazio = desde a 1ª venda.
    ir_ano_inicio: int | None = None
    # BDR com as regras de ações (isenção de R$ 20 mil); a RFB não estende a isenção a BDR.
    ir_bdr_como_acao: bool = False
    # Soma as vendas de day trade ao limite de isenção de R$ 20 mil das ações.
    ir_daytrade_no_limite: bool = False
    # Soma as vendas de opções ao limite de R$ 20 mil.
    ir_opcoes_no_limite: bool = False
    # Soma as vendas de outras classes de renda variável (BDR e ETF) ao limite de R$ 20 mil.
    ir_outras_classes_no_limite: bool = False
    # Venda de direito de subscrição de FII até 28/09/2021 como isenta (padrão: tributa como FII, 20%).
    ir_subscricao_fii_isenta: bool = False
    # Alertas: vazio desliga. Desvio entre peso atual e alvo dos books (pontos percentuais).
    alerta_desvio_pp: int | None = 5
    # Renda fixa vencendo nos próximos N dias.
    alerta_vencimento_dias: int | None = 30
    # Cotação automática de posição aberta sem atualização há mais de N dias.
    alerta_cotacao_dias: int | None = 5


def _ler(texto: str, tipo):
    if tipo is bool:
        return texto == "1"
    if tipo is date:
        return date.fromisoformat(texto) if texto else None
    if tipo is int:
        return int(texto) if texto else None
    return texto


def _escrever(valor) -> str:
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, date):
        return valor.isoformat()
    return "" if valor is None else str(valor)


_TIPOS = {
    "caixa_data_inicio": date,
    "caixa_no_portfolio": bool,
    "ir_ano_inicio": int,
    "ir_bdr_como_acao": bool,
    "ir_daytrade_no_limite": bool,
    "ir_opcoes_no_limite": bool,
    "ir_outras_classes_no_limite": bool,
    "ir_subscricao_fii_isenta": bool,
    "alerta_desvio_pp": int,
    "alerta_vencimento_dias": int,
    "alerta_cotacao_dias": int,
}


def carregar(sessao: Session) -> Parametros:
    gravados = {p.chave: p.valor for p in sessao.scalars(select(Parametro).where(Parametro.chave.in_(_TIPOS)))}
    return Parametros(**{chave: _ler(texto, _TIPOS[chave]) for chave, texto in gravados.items()})


def salvar(sessao: Session, parametros: Parametros) -> Parametros:
    for chave in _TIPOS:
        sessao.merge(Parametro(chave=chave, valor=_escrever(getattr(parametros, chave))))
    sessao.commit()
    return parametros
