"""CDI diario (SGS 12, % a.d.), convertido em fracao, sem interpolar dias nao publicados."""

from bisect import bisect_left
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal, localcontext

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import insert_upsert
from ..models import CdiDiario, CoberturaCdi


class CdiIndisponivel(ValueError):
    pass


def gravar(sessao: Session, inicio: date, fim: date, taxas: Mapping[date, Decimal]) -> None:
    if fim < inicio or not taxas:
        raise CdiIndisponivel("CDI diário sem dados. Atualize o histórico de índices.")
    if any(
        not inicio <= dia <= fim or not taxa.is_finite() or taxa <= -1
        for dia, taxa in taxas.items()
    ):
        raise ValueError("Taxa CDI diária inválida ou fora do intervalo consultado")
    linhas = [{"data": dia, "taxa": taxa} for dia, taxa in sorted(taxas.items())]
    for i in range(0, len(linhas), 500):
        lote = insert_upsert(sessao, CdiDiario).values(linhas[i:i + 500])
        sessao.execute(lote.on_conflict_do_update(index_elements=["data"], set_={"taxa": lote.excluded.taxa}))
    intervalos = [(c.inicio, c.fim) for c in sessao.scalars(select(CoberturaCdi))]
    unidos: list[tuple[date, date]] = []
    for a, b in sorted([*intervalos, (inicio, fim)]):
        if unidos and a <= unidos[-1][1] + timedelta(days=1):
            unidos[-1] = (unidos[-1][0], max(b, unidos[-1][1]))
        else:
            unidos.append((a, b))
    sessao.execute(delete(CoberturaCdi))
    sessao.add_all(CoberturaCdi(inicio=a, fim=b) for a, b in unidos)
    sessao.commit()


class CurvaCdi:
    def __init__(self, sessao: Session, percentual: Decimal = Decimal(1), taxa_aa: Decimal = Decimal(0)):
        self.cobertura = [(c.inicio, c.fim) for c in sessao.scalars(select(CoberturaCdi))]
        self.datas: list[date] = []
        self.acumulados = [Decimal(1)]
        with localcontext() as ctx:
            ctx.prec = 40
            adicional = (1 + taxa_aa) ** (Decimal(1) / 252)
            for dia, taxa in sessao.execute(select(CdiDiario.data, CdiDiario.taxa).order_by(CdiDiario.data)):
                fator = (1 + taxa * percentual) * adicional
                if fator <= 0:
                    raise ValueError("Fator CDI diário inválido")
                self.datas.append(dia)
                self.acumulados.append(self.acumulados[-1] * fator)

    def fator(self, inicio: date, fim: date) -> Decimal:
        """Inclui a data inicial e exclui resgate/saldo final; só dias publicados pelo BCB."""
        if fim <= inicio:
            return Decimal(1)
        if not any(a <= inicio and b >= fim - timedelta(days=1) for a, b in self.cobertura):
            raise CdiIndisponivel(
                f"CDI diário não consultado de {inicio:%d/%m/%Y} a {fim - timedelta(days=1):%d/%m/%Y}. "
                "Atualize o histórico completo de índices em Configurações → Atualizações.",
            )
        with localcontext() as ctx:
            ctx.prec = 40
            return self.acumulados[bisect_left(self.datas, fim)] / self.acumulados[bisect_left(self.datas, inicio)]
