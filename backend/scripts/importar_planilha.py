"""Importa a planilha de investimentos (.xlsx exportado do Google Sheets) para o banco.

Idempotente: cada linha recebe um hash; reimportar a mesma planilha não duplica lançamentos.

Uso (dentro de backend/):
    ..\\.venv\\Scripts\\python.exe -m scripts.importar_planilha "..\\Ref\\planilha.xlsx" --investidor "Nome"
"""

import argparse
import hashlib
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Ativo,
    Corretora,
    DarfPago,
    IndiceMensal,
    Investidor,
    MovCaixa,
    Operacao,
    Parametro,
    PrejuizoInicial,
    Provento,
)
from app.services import aluguel
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

# config.parâmetros → parâmetros de IR do app (rótulo sem acento, em maiúsculas → chave).
PARAMETROS_DARF = {
    "SOMAR VENDAS DE DAYRADE NO LIMITE": "ir_daytrade_no_limite",
    "SOMAR VENDAS DE OUTRAS CLASSES NO LIMITE": "ir_outras_classes_no_limite",
    "SOMAR VENDAS DE OPCOES NO LIMITE": "ir_opcoes_no_limite",
    "VENDA DE SUBSCRICAO DE FII COMO ISENTO": "ir_subscricao_fii_isenta",
    "CONSIDERAR BDR COMO ACAO": "ir_bdr_como_acao",
    "ANO DE INICIO DOS CALCULOS DARF": "ir_ano_inicio",
}

# Colunas do quadro "Transportar o prejuízo" (config.parâmetros) → grupo de compensação.
PREJUIZO_COLUNAS = {7: "COMUM", 8: "DAYTRADE", 9: "FII"}

# "Histórico de rendimentos": quadro de criptos com ticker (J), preço em USD (K) e quantidade (L).
COLUNA_CRIPTO = 10  # J
ULTIMA_LINHA_CRIPTO = 400

# Ticker → ID CoinGecko (o ticker sozinho é ambíguo no CoinGecko). Os demais ficam sem ID e são
# vinculados pela tela Cripto.
COINGECKO_IDS = {
    "BTC": "bitcoin", "ETH": "ethereum", "ADA": "cardano", "BNB": "binancecoin", "XRP": "ripple",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "DOGE": "dogecoin", "LINK": "chainlink", "DASH": "dash",
    "BAT": "basic-attention-token", "NANO": "nano", "SOL": "solana", "TRX": "tron", "SUI": "sui",
    "ZEC": "zcash", "HBAR": "hedera-hashgraph", "SHIB": "shiba-inu", "USDC": "usd-coin",
}


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
        raise ValueError(f"Valor numérico inválido: {valor!r}") from None


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
    yield from enumerate(wb[aba].iter_rows(min_row=primeira_linha, values_only=True), start=primeira_linha)


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

    def importar_aluguel(self, wb) -> None:
        """Aba Página117 (extrato da corretora): remuneração, IRRF e taxa do BTC → provento ALUGUEL por data e ativo."""
        aba = next((n for n in wb.sheetnames if sem_acento(n).startswith("PAGINA117")), None)
        if aba is None:
            return
        brutas = []
        for numero, l in linhas(wb, aba, 2):
            dia, historico, ticker = data(col(l, 1)), texto(col(l, 2)), texto(col(l, 3))
            # Só converte o valor das linhas de BTC (TEDs, multas etc. podem ter formatos diversos).
            if dia and historico and ticker and aluguel.classificar(historico):
                brutas.append((numero, dia, historico, ticker, decimal(col(l, 4))))

        for g in aluguel.agrupar(brutas):
            ativo, candidatos = aluguel.ativo_por_raiz(self.ativos.values(), g.raiz, g.ticker)
            if len(candidatos) > 1:
                self.avisos.append(f"aluguel {g.raiz}: vários tickers ({', '.join(candidatos)}) — usado {ativo.ticker}")
            if ativo is None:
                self.avisos.append(f"aluguel {g.raiz} em {g.data:%d/%m/%Y}: ativo não cadastrado — ignorado")
                continue
            hash_ = self._hash(aba, g.data, g.raiz, g.valor, g.irrf, g.taxas)
            if not self._novo(Provento, hash_):
                continue
            self.sessao.add(Provento(
                investidor=self.investidor, ativo=ativo, data_pagamento=g.data, evento="ALUGUEL", valor=g.valor,
                irrf=g.irrf, taxas=g.taxas, moeda="BRL", cambio=Decimal(1), origem=ORIGEM, hash_origem=hash_,
            ))
            self.estatisticas["aluguéis (BTC) importados"] += 1

    def _do_investidor(self, cpf) -> bool:
        cpf = re.sub(r"\D", "", texto(cpf) or "")
        return not cpf or cpf == (self.investidor.cpf or "")

    def importar_darfs(self, wb) -> None:
        """Aba darfs.: pagamento sem competência; assume o mês anterior ao pagamento (vencimento usual)."""
        existentes = {
            (d.data_pagamento, d.valor)
            for d in self.sessao.scalars(select(DarfPago).where(DarfPago.investidor_id == self.investidor.id))
        }
        for _, l in linhas(wb, "darfs.", 4):
            dia, valor = data(col(l, 1)), col(l, 2)
            if not dia or valor in (None, "") or not self._do_investidor(col(l, 0)):
                continue
            valor = decimal(valor)
            if (dia, valor) in existentes:
                self.estatisticas["darf_pago já existentes"] += 1
                continue
            competencia = (dia.replace(day=1) - timedelta(days=1)).replace(day=1)
            self.sessao.add(DarfPago(investidor_id=self.investidor.id, competencia=competencia, data_pagamento=dia, valor=valor))
            existentes.add((dia, valor))
            self.estatisticas["DARFs pagos importados"] += 1

    def importar_parametros_ir(self, wb) -> None:
        """config.parâmetros: regras de DARF e prejuízo transportado. Não sobrescreve o que já foi definido no app."""
        aba = next((n for n in wb.sheetnames if sem_acento(n).startswith("CONFIG.PARAMETROS")), None)
        if aba is None:
            return
        no_quadro_prejuizo = False
        for _, l in linhas(wb, aba, 1):
            rotulo = sem_acento(texto(col(l, 0)) or "")
            chave = next((c for prefixo, c in PARAMETROS_DARF.items() if rotulo.startswith(prefixo)), None)
            if chave and col(l, 4) is not None and self.sessao.get(Parametro, chave) is None:
                v = col(l, 4)
                valor = str(int(v)) if chave == "ir_ano_inicio" else ("1" if v is True else "0")
                self.sessao.add(Parametro(chave=chave, valor=valor))
                self.estatisticas["parâmetros de IR importados"] += 1

            cpf = sem_acento(texto(col(l, 6)) or "")
            if "TRANSPORTAR O PREJUIZO" in cpf:
                no_quadro_prejuizo = True
                continue
            dono = cpf == "UNICO INVESTIDOR" or (cpf.isdigit() and self._do_investidor(cpf))
            if not (no_quadro_prejuizo and dono):
                continue
            for i, grupo in PREJUIZO_COLUNAS.items():
                valor = abs(decimal(col(l, i)))
                if valor and self.sessao.get(PrejuizoInicial, (self.investidor.id, grupo)) is None:
                    self.sessao.add(PrejuizoInicial(investidor_id=self.investidor.id, grupo=grupo, valor=valor))
                    self.estatisticas["prejuízos iniciais importados"] += 1
            if decimal(col(l, 10)):
                self.avisos.append("config.parâmetros: 'darf saldo' transportado não tem equivalente — lance como DARF a pagar")

    def importar_cripto(self, wb, abertura: date) -> None:
        """Histórico de rendimentos (J:L): posição de abertura de cada cripto pelo preço da planilha.

        A planilha não guarda custo nem data de compra: o preço médio deve ser revisado depois no app.
        Uma única abertura por ticker — reimportar não duplica nem altera posições já lançadas.
        """
        aba = next((n for n in wb.sheetnames if sem_acento(n).startswith("HISTORICO DE RENDIMENTOS")), None)
        if aba is None:
            return
        cambio = None
        no_quadro = False
        usados = {a.coingecko_id for a in self.ativos.values() if a.coingecko_id}
        linhas_aba = wb[aba].iter_rows(
            min_row=1, max_row=ULTIMA_LINHA_CRIPTO, min_col=COLUNA_CRIPTO, max_col=COLUNA_CRIPTO + 2, values_only=True,
        )
        for n, (ticker, preco, qtd) in enumerate(linhas_aba, start=1):
            numericos = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (preco, qtd))
            if not (isinstance(ticker, str) and ticker.strip() and numericos):
                if no_quadro:
                    break
                if isinstance(ticker, (int, float)) and not isinstance(ticker, bool) and 1 < ticker < 20:
                    cambio = decimal(ticker)  # cotação USD/BRL logo acima do quadro
                continue
            no_quadro = True
            ticker, preco, qtd = ticker.strip().upper(), decimal(preco), decimal(qtd)
            if qtd <= 0 or preco <= 0:
                continue
            if cambio is None:
                self.avisos.append(f"{aba}: cotação USD/BRL não encontrada acima do quadro de criptos — ignorado")
                return
            existente = self.ativos.get(ticker)
            if existente is not None and existente.classe != "CRIPTO":
                self.avisos.append(f"{aba} linha {n}: {ticker} já cadastrado como {existente.classe} — ignorado")
                continue
            hash_ = self._hash("cripto-abertura", ticker)
            if not self._novo(Operacao, hash_):
                continue
            ativo = self.ativo(ticker, classe="CRIPTO", moeda="USD")
            ativo.mercado, ativo.cotacao_automatica = None, True
            if ativo.coingecko_id is None and COINGECKO_IDS.get(ticker) not in (None, *usados):
                ativo.coingecko_id = COINGECKO_IDS[ticker]
                usados.add(ativo.coingecko_id)
            if ativo.coingecko_id is None:
                self.avisos.append(f"{ticker}: sem ID CoinGecko — vincule na tela Cripto para ter cotação")
            self.sessao.add(Operacao(
                investidor=self.investidor, ativo=ativo, data=abertura, evento="C", quantidade=qtd, preco=preco,
                taxas=Decimal(0), irrf=Decimal(0), moeda="USD", cambio=cambio, daytrade=False,
                observacao="Posição de abertura (planilha sem custo de compra): revise o preço médio",
                origem=ORIGEM, hash_origem=hash_,
            ))
            self.estatisticas["criptos importadas"] += 1


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
    parser.add_argument(
        "--data-cripto", type=date.fromisoformat, default=date.today(),
        help="Data (AAAA-MM-DD) da posição de abertura das criptos; padrão: hoje",
    )
    parser.add_argument(
        "--somente-cripto", action="store_true",
        help="Importa só as criptos (Histórico de rendimentos), sem reprocessar as demais abas",
    )
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
        if not args.somente_cripto:
            imp.importar_cadastro_ativos(wb)
            imp.importar_operacoes(wb, "op.normal", daytrade=False)
            imp.importar_operacoes(wb, "op.daytrade", daytrade=True)
            imp.importar_proventos(wb)
            imp.importar_caixa(wb)
            imp.importar_indices(wb)
            imp.importar_aluguel(wb)
            imp.importar_darfs(wb)
            imp.importar_parametros_ir(wb)
        imp.importar_cripto(wb, args.data_cripto)
        sessao.flush()

        print("\nResumo:")
        for chave, valor in sorted(imp.estatisticas.items()):
            print(f"  {chave:<32} {valor}")
        for aviso in imp.avisos:
            print(f"  AVISO: {aviso}")

        divergencias = [] if args.somente_cripto else conciliar(sessao, wb, investidor)
        if divergencias:
            print(f"{len(divergencias)} divergência(s):")
            for d in divergencias:
                print("  " + d)
        elif not args.somente_cripto:
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
