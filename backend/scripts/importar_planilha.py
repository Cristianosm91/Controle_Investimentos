"""Importa a planilha de investimentos (.xlsx exportado do Google Sheets) para o banco.

Idempotente: cada linha recebe um hash; reimportar a mesma planilha não duplica lançamentos.

Uso (dentro de backend/):
    ..\\.venv\\Scripts\\python.exe -m scripts.importar_planilha "..\\Ref\\planilha.xlsx" --investidor "Nome"
"""

import argparse
import hashlib
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Ativo, Corretora, IndiceMensal, Investidor, MovCaixa, Operacao, Provento
from app.services.carteira import carregar_posicoes

ORIGEM = "planilha"

MAPA_EVENTO_OPERACAO = {
    "C": "C",
    "V": "V",
    "S/I": "DESDOBRAMENTO",
    "BN": "BONIFICACAO",
    "AM": "AMORTIZACAO",
    "AT": "TRANSFERENCIA",
    "CISAO": "CISAO",
    "V.SUB": "VENDA_SUBSCRICAO",
}

MAPA_EVENTO_PROVENTO = {
    "RENDIMENTO": "RENDIMENTO",
    "JSCP": "JSCP",
    "JCP": "JSCP",
    "DIVIDENDO": "DIVIDENDO",
    "BONIFICACAO": "BONIFICACAO",
    "REEMBOLSO(JSCP)": "REEMBOLSO_JSCP",
    "AMORTIZACAO": "AMORTIZACAO",
}

CORRETORA_INDEFINIDA = {"", "INFORMAR", "INDEFINIDO"}


# ---------- conversões ----------

def sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


def texto(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def decimal(valor) -> Decimal:
    if valor is None or valor == "":
        return Decimal(0)
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    s = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Valor numérico inválido: {valor!r}")


def data(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    s = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, formato).date()
        except ValueError:
            pass
    raise ValueError(f"Data inválida: {valor!r}")


def linhas(wb, aba: str, primeira_linha: int):
    if aba not in wb.sheetnames:
        print(f"  aba '{aba}' não encontrada — ignorada")
        return
    for n, linha in enumerate(wb[aba].iter_rows(min_row=primeira_linha, values_only=True), start=primeira_linha):
        yield n, linha


def col(linha, i):
    return linha[i] if i < len(linha) else None


# ---------- importador ----------

class Importador:
    def __init__(self, sessao: Session, investidor: Investidor):
        self.sessao = sessao
        self.investidor = investidor
        self.ativos = {a.ticker: a for a in sessao.scalars(select(Ativo))}
        self.corretoras = {c.nome: c for c in sessao.scalars(select(Corretora))}
        self.hashes = {
            modelo: set(sessao.scalars(select(modelo.hash_origem).where(modelo.hash_origem.is_not(None))))
            for modelo in (Operacao, Provento, MovCaixa)
        }
        self._ocorrencias: Counter[str] = Counter()
        self.estatisticas: Counter[str] = Counter()
        self.avisos: list[str] = []

    def _hash(self, aba: str, *campos) -> str:
        # Duas linhas idênticas são legítimas (ex.: duas compras iguais no dia); a ocorrência as diferencia.
        base = "|".join(str(c) for c in (aba, self.investidor.id, *campos))
        self._ocorrencias[base] += 1
        return hashlib.sha256(f"{base}|{self._ocorrencias[base]}".encode()).hexdigest()

    def ativo(self, ticker: str, classe=None, market_cod=None, moeda=None, **extras) -> Ativo:
        ticker = ticker.strip().upper()
        obj = self.ativos.get(ticker)
        if obj is None:
            obj = Ativo(ticker=ticker, classe="AÇÃO", moeda="BRL", cotacao_automatica=False)
            self.sessao.add(obj)
            self.ativos[ticker] = obj
            self.estatisticas["ativos novos"] += 1
        if classe:
            obj.classe = str(classe).strip().upper()
        if moeda:
            obj.moeda = moeda
        if market_cod and ":" in str(market_cod):
            obj.mercado = str(market_cod).split(":", 1)[0].strip().upper()
            obj.cotacao_automatica = True
        for campo, valor in extras.items():
            if valor:
                setattr(obj, campo, valor)
        return obj

    def corretora(self, nome) -> Corretora | None:
        nome = (texto(nome) or "").upper()
        if nome in CORRETORA_INDEFINIDA:
            return None
        obj = self.corretoras.get(nome)
        if obj is None:
            obj = Corretora(nome=nome)
            self.sessao.add(obj)
            self.sessao.flush()
            self.corretoras[nome] = obj
        return obj

    def _novo(self, modelo, hash_: str) -> bool:
        if hash_ in self.hashes[modelo]:
            self.estatisticas[f"{modelo.__tablename__} já existentes"] += 1
            return False
        self.hashes[modelo].add(hash_)
        return True

    # --- abas ---

    def importar_cadastro_ativos(self, wb) -> None:
        for _, l in linhas(wb, "ativos.", 3):
            ticker = texto(col(l, 2))
            if not ticker:
                continue
            self.ativo(
                ticker,
                classe=texto(col(l, 5)),
                market_cod=texto(col(l, 4)),
                moeda=texto(col(l, 11)),
                nome=texto(col(l, 14)),
                setor=texto(col(l, 12)),
                subsetor=texto(col(l, 13)),
            )

    def importar_operacoes(self, wb, aba: str, daytrade: bool) -> None:
        for n, l in linhas(wb, aba, 5):
            ticker, dia, evento_bruto = texto(col(l, 1)), data(col(l, 2)), texto(col(l, 3))
            if not (ticker and dia and evento_bruto):
                continue
            qtd = decimal(col(l, 4))
            if daytrade:
                evento = "C" if qtd > 0 else "V"
            else:
                evento = MAPA_EVENTO_OPERACAO.get(sem_acento(evento_bruto))
                if evento is None:
                    self.avisos.append(f"{aba} linha {n}: evento '{evento_bruto}' desconhecido — ignorada")
                    continue
            preco, taxas, irrf = decimal(col(l, 5)), decimal(col(l, 6)), decimal(col(l, 8))
            moeda = texto(col(l, 9)) or "BRL"
            cambio = decimal(col(l, 22)) if moeda != "BRL" else Decimal(1)
            hash_ = self._hash(aba, ticker, dia, evento_bruto, qtd, preco, taxas, irrf)
            if not self._novo(Operacao, hash_):
                continue
            ativo = self.ativo(ticker, classe=texto(col(l, 12)), market_cod=texto(col(l, 13)), moeda=moeda)
            self.sessao.add(Operacao(
                investidor=self.investidor, ativo=ativo, corretora=self.corretora(col(l, 7)),
                data=dia, evento=evento, quantidade=qtd, preco=preco, taxas=taxas, irrf=irrf, moeda=moeda,
                cambio=cambio or Decimal(1),
                daytrade=daytrade, observacao=texto(col(l, 10)), origem=ORIGEM, hash_origem=hash_,
            ))
            self.estatisticas[f"{aba} importadas"] += 1

    def importar_proventos(self, wb) -> None:
        for n, l in linhas(wb, "proventos", 5):
            ticker, dia, evento_bruto = texto(col(l, 1)), data(col(l, 2)), texto(col(l, 3))
            if not (ticker and dia and evento_bruto):
                continue
            evento = MAPA_EVENTO_PROVENTO.get(sem_acento(evento_bruto))
            if evento is None:
                self.avisos.append(f"proventos linha {n}: evento '{evento_bruto}' desconhecido — ignorada")
                continue
            valor, irrf, taxas = decimal(col(l, 4)), decimal(col(l, 5)), decimal(col(l, 6))
            moeda = texto(col(l, 7)) or "BRL"
            cambio = (decimal(col(l, 14)) if moeda != "BRL" else Decimal(1)) or Decimal(1)
            hash_ = self._hash("proventos", ticker, dia, evento, valor, irrf, taxas)
            if not self._novo(Provento, hash_):
                continue
            ativo = self.ativo(ticker, classe=texto(col(l, 13)), market_cod=texto(col(l, 12)))
            self.sessao.add(Provento(
                investidor=self.investidor, ativo=ativo, corretora=self.corretora(col(l, 8)),
                data_pagamento=dia, data_com=data(col(l, 9)), evento=evento, valor=valor, irrf=irrf, taxas=taxas,
                moeda=moeda, cambio=cambio, observacao=texto(col(l, 10)), origem=ORIGEM, hash_origem=hash_,
            ))
            self.estatisticas["proventos importados"] += 1

    def importar_caixa(self, wb) -> None:
        for _, l in linhas(wb, "caixa", 5):
            dia, evento, valor = data(col(l, 1)), texto(col(l, 2)), col(l, 3)
            if not (dia and evento and valor not in (None, "")):
                continue
            valor = decimal(valor)
            hash_ = self._hash("caixa", dia, evento, valor)
            if not self._novo(MovCaixa, hash_):
                continue
            corretora = self.corretora(col(l, 5))
            self.sessao.add(MovCaixa(
                investidor_id=self.investidor.id, corretora_id=corretora.id if corretora else None,
                data=dia, evento=sem_acento(evento), valor=valor, moeda=texto(col(l, 4)) or "BRL",
                observacao=texto(col(l, 6)), origem=ORIGEM, hash_origem=hash_,
            ))
            self.estatisticas["caixa importados"] += 1

    def importar_indices(self, wb) -> None:
        for _, l in linhas(wb, "index.", 3):
            fim_mes = data(col(l, 0))
            if not fim_mes:
                continue
            competencia = fim_mes.replace(day=1)
            obj = self.sessao.get(IndiceMensal, competencia) or IndiceMensal(competencia=competencia)
            obj.ibov = decimal(col(l, 2)) if col(l, 2) not in (None, "") else obj.ibov
            obj.ifix = decimal(col(l, 3)) if col(l, 3) not in (None, "") else obj.ifix
            obj.cdi = decimal(col(l, 5)) if col(l, 5) not in (None, "") else obj.cdi
            obj.ipca = decimal(col(l, 6)) if col(l, 6) not in (None, "") else obj.ipca
            self.sessao.merge(obj)
            self.estatisticas["índices mensais"] += 1


# ---------- conciliação ----------

def conciliar(sessao: Session, wb, investidor: Investidor) -> list[str]:
    """Compara posição e PM calculados com a aba `dados.` da planilha."""
    esperado: dict[str, tuple[Decimal, Decimal]] = {}
    for _, l in linhas(wb, "dados.", 4):
        ticker = texto(col(l, 0))
        if ticker and col(l, 9) not in (None, ""):
            esperado[ticker.upper()] = (decimal(col(l, 9)), decimal(col(l, 10)))

    ativos = {a.id: a.ticker for a in sessao.scalars(select(Ativo))}
    calculado = {
        ativos[a]: p for (_, a), p in carregar_posicoes(sessao, [investidor.id]).items() if p.aberta
    }

    divergencias = []
    for ticker in sorted(set(esperado) | set(calculado)):
        qtd_e, pm_e = esperado.get(ticker, (Decimal(0), Decimal(0)))
        p = calculado.get(ticker)
        qtd_c, pm_c = (p.quantidade, p.preco_medio) if p else (Decimal(0), Decimal(0))
        if abs(qtd_e - qtd_c) > Decimal("0.000001") or abs(pm_e - pm_c) > Decimal("0.01"):
            divergencias.append(
                f"{ticker:<10} planilha qtd={qtd_e:>12.4f} pm={pm_e:>12.4f} | app qtd={qtd_c:>12.4f} pm={pm_c:>12.4f}"
            )
    print(f"\nConciliação com 'dados.': {len(esperado)} posições na planilha, {len(calculado)} no app")
    return divergencias


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivo", type=Path, help="Caminho do .xlsx")
    parser.add_argument("--investidor", required=True, help="Nome do investidor dono dos lançamentos")
    parser.add_argument("--simular", action="store_true", help="Executa e concilia sem gravar")
    args = parser.parse_args(argv)

    if not args.arquivo.is_file():
        print(f"Arquivo não encontrado: {args.arquivo}", file=sys.stderr)
        return 2

    print(f"Lendo {args.arquivo.name} ...")
    wb = openpyxl.load_workbook(args.arquivo, read_only=True, data_only=True)

    with SessionLocal() as sessao:
        investidor = sessao.scalar(select(Investidor).where(Investidor.nome == args.investidor))
        if investidor is None:
            investidor = Investidor(nome=args.investidor)
            sessao.add(investidor)
            sessao.flush()
            print(f"Investidor '{args.investidor}' criado (id {investidor.id})")

        imp = Importador(sessao, investidor)
        imp.importar_cadastro_ativos(wb)
        imp.importar_operacoes(wb, "op.normal", daytrade=False)
        imp.importar_operacoes(wb, "op.daytrade", daytrade=True)
        imp.importar_proventos(wb)
        imp.importar_caixa(wb)
        imp.importar_indices(wb)
        sessao.flush()

        print("\nResumo:")
        for chave, valor in sorted(imp.estatisticas.items()):
            print(f"  {chave:<32} {valor}")
        for aviso in imp.avisos:
            print(f"  AVISO: {aviso}")

        divergencias = conciliar(sessao, wb, investidor)
        if divergencias:
            print(f"{len(divergencias)} divergência(s):")
            for d in divergencias:
                print("  " + d)
        else:
            print("Sem divergências de quantidade/preço médio.")

        if args.simular:
            sessao.rollback()
            print("\nSimulação: nada foi gravado.")
        else:
            sessao.commit()
            print("\nImportação gravada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
