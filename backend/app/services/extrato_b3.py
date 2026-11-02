"""Importação de relatórios da B3 e de planilhas de operações (.xlsx).

Fluxo: `analisar` monta a prévia (nada é gravado); `importar` reanalisa o mesmo arquivo e grava as linhas novas
(e as "verificar" escolhidas). Duplicidade é conferida contra tudo o que já existe (planilha, digitação ou
importação anterior) pela soma diária de quantidade/valor por ativo e evento — a planilha pode ter agrupado
execuções do mesmo dia — e por um hash por linha, que torna a reimportação idempotente.
"""

import hashlib
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from itertools import islice

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Ativo, Corretora, Investidor, LoteImportacao, Operacao, Provento
from ..seguranca import LINHAS_MAXIMAS, tamanho_descompactado_excedido
from . import lotes

ORIGEM_B3 = "b3"
ORIGEM_PLANILHA_OPERACOES = "planilha_operacoes"
TAMANHO_MAXIMO = 10 * 1024 * 1024
_TOLERANCIA_VALOR = Decimal("0.05")


class ExtratoInvalido(Exception):
    pass


def _normalizar(texto) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


# Movimentação → provento (somente créditos).
_PROVENTOS = {
    "dividendo": "DIVIDENDO",
    "juros sobre capital proprio": "JSCP",
    "rendimento": "RENDIMENTO",
    # Provento repassado pelo tomador das ações emprestadas (BTC); a planilha usava "Reembolso de JSCP".
    "reembolso": "REEMBOLSO_JSCP",
}
# Movimentação → operação (somente créditos).
_OPERACOES_MOVIMENTACAO = {"amortizacao": "AMORTIZACAO", "desdobro": "DESDOBRAMENTO"}
_MOTIVOS_IGNORADOS = {
    "transferencia - liquidacao": "Liquidação de compra/venda: use o relatório de Negociação",
    "emprestimo": "Aluguel de ações (BTC): lance em Proventos → Aluguel",
    "grupamento": "Grupamento: lance manualmente (Desdobramento/Grupamento com quantidade negativa)",
    "bonificacao em ativos": "Bonificação: lance manualmente com o custo informado pela empresa",
    "fracao em ativos": "Fração de ativos: lance manualmente",
    "leilao de fracao": "Leilão de fração: lance manualmente como venda",
    "incorporacao": "Incorporação: lance manualmente (Transferência/Troca de ticker)",
    "atualizacao": "Atualização de posição: sem efeito financeiro",
    "transferencia": "Transferência de custódia: sem efeito financeiro",
    "cessao de direitos": "Direito de subscrição: lance manualmente",
    "cessao de direitos - solicitada": "Direito de subscrição: lance manualmente",
    "direito de subscricao": "Direito de subscrição: lance manualmente",
    "direitos de subscricao - exercido": "Subscrição: lance a compra manualmente",
    "direitos de subscricao - nao exercido": "Direito de subscrição não exercido: sem efeito",
    "recibo de subscricao": "Subscrição: lance a compra manualmente",
}
_MERCADOS_ACEITOS = {"mercado a vista", "mercado fracionario", "opcao de compra", "opcao de venda"}

_COLUNAS_NEGOCIACAO = {
    "data do negocio": "data", "tipo de movimentacao": "tipo", "mercado": "mercado", "instituicao": "instituicao",
    "codigo de negociacao": "codigo", "quantidade": "quantidade", "preco": "preco", "valor": "valor",
}
_COLUNAS_MOVIMENTACAO = {
    "entrada/saida": "sentido", "data": "data", "movimentacao": "movimentacao", "produto": "produto",
    "instituicao": "instituicao", "quantidade": "quantidade", "preco unitario": "preco", "valor da operacao": "valor",
}
# Relatório "Proventos recebidos": só créditos; o valor já é líquido.
_COLUNAS_PROVENTOS = {
    "produto": "produto", "pagamento": "data", "tipo de evento": "movimentacao", "instituicao": "instituicao",
    "quantidade": "quantidade", "preco unitario": "preco", "valor liquido": "valor",
}
_COLUNAS_PLANILHA_OPERACOES = {
    "ativo": "ticker", "date": "data", "evento": "evento", "qtd": "quantidade", "preco": "preco",
    "taxas": "taxas", "corretora": "instituicao", "irrf": "irrf", "moeda": "moeda",
}
_RELATORIOS = (
    ("NEGOCIACAO", _COLUNAS_NEGOCIACAO), ("MOVIMENTACAO", _COLUNAS_MOVIMENTACAO), ("PROVENTOS", _COLUNAS_PROVENTOS),
    ("PLANILHA_OPERACOES", _COLUNAS_PLANILHA_OPERACOES),
)


@dataclass
class Linha:
    numero: int
    relatorio: str  # NEGOCIACAO | MOVIMENTACAO | PROVENTOS | PLANILHA_OPERACOES
    descricao: str
    data: date | None
    ticker: str | None
    tipo: str  # OPERACAO | PROVENTO | IGNORADA
    evento: str | None = None
    quantidade: Decimal = Decimal(0)
    preco: Decimal = Decimal(0)
    valor: Decimal = Decimal(0)
    taxas: Decimal = Decimal(0)
    irrf: Decimal = Decimal(0)
    moeda: str = "BRL"
    origem: str = ORIGEM_B3
    instituicao: str | None = None
    nome_produto: str | None = None
    classe: str | None = None
    daytrade: bool = False
    status: str = "novo"  # novo | duplicado | verificar | ignorado
    motivo: str | None = None
    hash: str | None = None
    evento_original: str | None = None


@dataclass
class Previa:
    relatorio: str
    linhas: list[Linha]
    ativos_novos: dict[str, str] = field(default_factory=dict)
    corretoras_novas: list[str] = field(default_factory=list)


# ---------- Leitura do arquivo ----------

def _decimal(valor) -> Decimal | None:
    if valor is None:
        return None
    if isinstance(valor, int | float | Decimal):
        return Decimal(str(valor))
    texto = str(valor).replace("R$", "").replace("\u00a0", "").strip()
    if texto in ("", "-", "—"):
        return None
    # Texto da B3 é pt-BR: vírgula decimal e ponto de milhar ("1.350" = mil trezentos e cinquenta).
    if "," in texto or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation as erro:
        raise ExtratoInvalido(f"Valor numérico inválido: {valor!r}") from erro


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _ler_planilha(conteudo: bytes) -> list[tuple]:
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ExtratoInvalido("Arquivo maior que 10 MB")
    if not zipfile.is_zipfile(io.BytesIO(conteudo)):
        raise ExtratoInvalido("O arquivo não é uma planilha .xlsx (exporte o relatório da B3 em Excel).")
    try:
        excedido = tamanho_descompactado_excedido(conteudo)
    except zipfile.BadZipFile as erro:
        raise ExtratoInvalido("Planilha .xlsx corrompida") from erro
    if excedido:
        raise ExtratoInvalido("Planilha grande demais quando descompactada")
    try:
        livro = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception as erro:
        raise ExtratoInvalido(f"Não foi possível abrir a planilha: {erro}") from erro
    try:
        planilha = livro.worksheets[0]
        # A B3 grava a dimensão como "A1": sem isto o modo read_only lê só a primeira linha.
        planilha.reset_dimensions()
        linhas = [tuple(linha) for linha in islice(planilha.iter_rows(values_only=True), LINHAS_MAXIMAS + 1)]
    finally:
        livro.close()
    if len(linhas) > LINHAS_MAXIMAS:
        raise ExtratoInvalido(f"Planilha com mais de {LINHAS_MAXIMAS} linhas: divida o período do relatório")
    return linhas


def _mapear_cabecalho(linhas: list[tuple]) -> tuple[str, int, dict[str, int]]:
    for indice, linha in enumerate(linhas[:20]):
        nomes = {_normalizar(c): i for i, c in enumerate(linha) if c is not None}
        for relatorio, colunas in _RELATORIOS:
            if all(nome in nomes for nome in colunas):
                return relatorio, indice, {campo: nomes[nome] for nome, campo in colunas.items()}
    raise ExtratoInvalido(
        "Formato não reconhecido. Use os relatórios Negociação, Movimentação ou Proventos recebidos da Área do "
        "Investidor da B3, ou a planilha de operações do app (.xlsx)."
    )


def _ticker_negociacao(codigo: str, mercado: str) -> str:
    codigo = codigo.strip().upper()
    if mercado == "mercado fracionario" and re.fullmatch(r"[A-Z0-9]{4}\d{1,2}F", codigo):
        return codigo[:-1]
    return codigo


def _classe_inferida(ticker: str, nome: str | None, mercado: str | None = None) -> str:
    nome_n = _normalizar(nome)
    if mercado and mercado.startswith("opcao"):
        return "OPÇÃO"
    if "fiagro" in nome_n:
        return "FIAGRO"
    if re.search(r"imobiliari|\bfii\b|\bimob\b", nome_n):
        return "FII"
    if re.search(r"\betf\b|indice|index|ishares", nome_n):
        return "ETF"
    if re.fullmatch(r"[A-Z]{4}3[2-5]|[A-Z]{4}39", ticker):
        return "BDR"
    if ticker.endswith("11") and not nome_n:
        return "FII"
    return "AÇÃO"


def ler(conteudo: bytes) -> tuple[str, list[Linha]]:
    planilha = _ler_planilha(conteudo)
    relatorio, cabecalho, colunas = _mapear_cabecalho(planilha)
    linhas: list[Linha] = []
    for numero, bruta in enumerate(planilha[cabecalho + 1:], start=cabecalho + 2):
        valor = {campo: (bruta[i] if i < len(bruta) else None) for campo, i in colunas.items()}
        if all(v in (None, "") for v in valor.values()):
            continue
        dia = _data(valor["data"])
        if dia is None:
            continue  # rodapé/total
        qtd = _decimal(valor["quantidade"]) or Decimal(0)
        preco = _decimal(valor["preco"]) or Decimal(0)
        total = _decimal(valor.get("valor"))
        instituicao = str(valor.get("instituicao") or "").strip() or None
        if relatorio == "NEGOCIACAO":
            linhas.append(_linha_negociacao(numero, dia, valor, qtd, preco, total, instituicao))
        elif relatorio == "PLANILHA_OPERACOES":
            linhas.append(_linha_planilha_operacoes(numero, dia, valor, qtd, preco, instituicao))
        else:
            if relatorio == "PROVENTOS":
                valor["sentido"] = "Credito"
            linhas.append(_linha_movimentacao(numero, dia, valor, qtd, preco, total, instituicao, relatorio))
    if not linhas:
        raise ExtratoInvalido("O relatório não tem lançamentos.")
    return relatorio, linhas


def _linha_negociacao(numero, dia, valor, qtd, preco, total, instituicao) -> Linha:
    tipo = _normalizar(valor["tipo"])
    mercado = _normalizar(valor["mercado"])
    codigo = str(valor["codigo"] or "").strip()
    descricao = f"{str(valor['tipo'] or '').strip()} · {str(valor['mercado'] or '').strip()}"
    linha = Linha(numero, "NEGOCIACAO", descricao, dia, None, "IGNORADA", instituicao=instituicao)
    if tipo not in ("compra", "venda") or not codigo:
        linha.status, linha.motivo = "ignorado", "Tipo de movimentação não reconhecido"
        return linha
    linha.ticker = _ticker_negociacao(codigo, mercado)
    if mercado not in _MERCADOS_ACEITOS:
        linha.status, linha.motivo = "ignorado", f"Mercado não suportado ({valor['mercado']}): lance manualmente"
        return linha
    if qtd <= 0 or preco <= 0:
        linha.status, linha.motivo = "ignorado", "Quantidade ou preço ausente"
        return linha
    linha.tipo, linha.evento = "OPERACAO", "C" if tipo == "compra" else "V"
    linha.quantidade = qtd if tipo == "compra" else -qtd
    linha.preco = preco
    linha.valor = total if total is not None else qtd * preco
    linha.classe = _classe_inferida(linha.ticker, None, mercado)
    return linha


def _linha_planilha_operacoes(numero, dia, valor, qtd, preco, instituicao) -> Linha:
    """Lê o layout simples: ativo, date, evento, qtd, preco, taxas, corretora, irrf, moeda."""
    from ..dominio import EVENTOS_PLANILHA_NAO_SUPORTADOS, EVENTOS_PLANILHA_OPERACOES

    ticker = str(valor["ticker"] or "").strip().upper()
    evento_bruto = str(valor.get("evento") or "").strip().upper()
    evento = EVENTOS_PLANILHA_OPERACOES.get(evento_bruto)
    moeda = str(valor.get("moeda") or "BRL").strip().upper()
    linha = Linha(
        numero, "PLANILHA_OPERACOES", "Planilha de operações", dia, ticker or None, "IGNORADA",
        instituicao=instituicao, moeda=moeda, origem=ORIGEM_PLANILHA_OPERACOES,
        evento_original=evento_bruto or None,
    )
    campos_invalidos = [
        nome
        for campo, nome in (
            ("qtd", "qtd"),
            ("preco", "preco"),
            ("taxas", "taxas"),
            ("irrf", "irrf"),
        )
        if valor.get(campo) not in (None, "") and _decimal(valor.get(campo)) is None
    ]
    if dia is None:
        linha.status, linha.motivo = "ignorado", f"Linha {numero}: data ausente ou inválida"
    elif not re.fullmatch(r"[A-Z0-9]{4,16}", ticker):
        linha.status, linha.motivo = "ignorado", f"Linha {numero}: ativo inválido ou ausente"
    elif not evento_bruto:
        linha.status, linha.motivo = "ignorado", f"Linha {numero}: coluna Evento vazia"
    elif campos_invalidos:
        linha.status, linha.motivo = (
            "ignorado",
            f"Linha {numero}: valor inválido no(s) campo(s) {', '.join(campos_invalidos)} "
            f"para o evento '{evento_bruto}'.",
        )
    elif evento is None:
        motivo = EVENTOS_PLANILHA_NAO_SUPORTADOS.get(evento_bruto)
        if motivo:
            linha.status, linha.motivo = (
                "ignorado",
                f"Linha {numero}: evento '{evento_bruto}' reconhecido, mas não suportado; {motivo}.",
            )
        else:
            linha.status, linha.motivo = (
                "ignorado",
                f"Linha {numero}: evento '{evento_bruto}' não reconhecido. Corrija a coluna Evento.",
            )
    elif moeda != "BRL":
        linha.status, linha.motivo = (
            "ignorado",
            f"Linha {numero}: moeda '{moeda}' não suportada; use BRL.",
        )
    else:
        taxas = (_decimal(valor.get("taxas")) or Decimal(0)).quantize(Decimal("0.01"))
        irrf = (_decimal(valor.get("irrf")) or Decimal(0)).quantize(Decimal("0.01"))
        quantidade = qtd
        daytrade = False

        if evento == "DAYTRADE":
            evento = "C" if qtd > 0 else "V"
            quantidade = qtd
            daytrade = True
            quantidade_valida = qtd != 0
            preco_valido = preco > 0
        elif evento in ("C", "V"):
            quantidade_valida = qtd > 0
            preco_valido = preco > 0
            quantidade = qtd if evento == "C" else -qtd
        elif evento == "BONIFICACAO":
            quantidade_valida = qtd > 0
            preco_valido = preco == 0
        elif evento == "DESDOBRAMENTO":
            quantidade_valida = qtd != 0
            preco_valido = preco == 0
        elif evento == "TRANSFERENCIA":
            quantidade_valida = qtd != 0
            preco_valido = preco >= 0
        elif evento == "AMORTIZACAO":
            quantidade_valida = qtd > 0
            preco_valido = preco < 0
        elif evento == "CISAO":
            quantidade_valida = qtd > 0
            preco_valido = preco <= 0
        else:
            quantidade_valida = qtd > 0
            preco_valido = preco >= 0
            quantidade = -qtd

        if taxas < 0 or irrf < 0:
            linha.status, linha.motivo = (
                "ignorado",
                f"Linha {numero}: taxas e IRRF não podem ser negativos para o evento '{evento_bruto}'.",
            )
        elif not quantidade_valida or not preco_valido:
            linha.status, linha.motivo = (
                "ignorado",
                f"Linha {numero}: quantidade/preço incompatíveis com o evento '{evento_bruto}'. "
                "Confira os sinais e os campos obrigatórios indicados nas instruções do modelo.",
            )
        else:
            linha.tipo, linha.evento = "OPERACAO", evento
            linha.quantidade = quantidade
            linha.preco, linha.valor = preco, abs(qtd * preco)
            linha.taxas, linha.irrf = taxas, irrf
            linha.daytrade = daytrade
            linha.classe = _classe_inferida(ticker, None)
    return linha


def _linha_movimentacao(numero, dia, valor, qtd, preco, total, instituicao, relatorio="MOVIMENTACAO") -> Linha:
    movimentacao = _normalizar(valor["movimentacao"])
    produto = str(valor["produto"] or "").strip()
    ticker, _, nome = produto.partition(" - ")
    ticker = ticker.strip().upper() or None
    credito = _normalizar(valor["sentido"]).startswith("credito")
    descricao = str(valor["movimentacao"] or "").strip()
    if relatorio == "MOVIMENTACAO":
        descricao += f" · {'Crédito' if credito else 'Débito'}"
    linha = Linha(
        numero, relatorio, descricao, dia, ticker, "IGNORADA", instituicao=instituicao,
        nome_produto=nome.strip() or None,
    )
    valor_total = total if total is not None else qtd * preco
    if _normalizar(produto).startswith("tesouro") or not ticker or not re.fullmatch(r"[A-Z0-9]{4,12}", ticker):
        linha.status, linha.motivo = "ignorado", "Renda fixa/Tesouro ou produto sem código de negociação"
    elif movimentacao in _PROVENTOS and credito:
        if valor_total <= 0:
            linha.status, linha.motivo = "ignorado", "Provento sem valor"
        else:
            linha.tipo, linha.evento, linha.valor = "PROVENTO", _PROVENTOS[movimentacao], valor_total
            if movimentacao == "reembolso":
                linha.motivo = "Reembolso de provento de ações emprestadas (BTC): confira se foi JCP ou dividendo"
    elif movimentacao in _OPERACOES_MOVIMENTACAO and credito:
        evento = _OPERACOES_MOVIMENTACAO[movimentacao]
        if qtd <= 0 or (evento == "AMORTIZACAO" and valor_total <= 0):
            linha.status, linha.motivo = "ignorado", "Quantidade ou valor ausente"
        else:
            linha.tipo, linha.evento, linha.quantidade = "OPERACAO", evento, qtd
            # Amortização reduz custo: preço negativo por cota (convenção do app).
            linha.preco = -(valor_total / qtd).quantize(Decimal("0.00000001")) if evento == "AMORTIZACAO" else Decimal(0)
            linha.valor = valor_total if evento == "AMORTIZACAO" else Decimal(0)
    else:
        linha.status = "ignorado"
        linha.motivo = _MOTIVOS_IGNORADOS.get(movimentacao) or (
            "Débito: sem lançamento correspondente no app" if not credito else
            f"Movimentação não importada ({valor['movimentacao']}): lance manualmente se necessário"
        )
    if linha.tipo != "IGNORADA" and ticker:
        linha.classe = _classe_inferida(ticker, linha.nome_produto)
    return linha


# ---------- Análise contra o banco ----------

def _nome_corretora(instituicao: str) -> str:
    palavras = [p for p in re.split(r"[\s\-/.]+", _normalizar(instituicao).upper()) if p]
    while palavras and palavras[0] in ("BANCO", "BCO"):
        palavras.pop(0)
    return (palavras[0] if palavras else instituicao.strip().upper())[:60]


def _hash(investidor_id: int, linha: Linha, ocorrencia: int) -> str:
    base = "|".join(
        str(x) for x in (
            linha.origem, investidor_id, linha.relatorio, linha.data, linha.ticker, linha.evento,
            linha.quantidade.normalize(), linha.preco.normalize(), linha.valor.normalize(), linha.taxas.normalize(),
            linha.irrf.normalize(), linha.moeda, linha.instituicao, ocorrencia,
        )
    )
    return hashlib.sha256(base.encode()).hexdigest()


def _marcar_daytrade(linhas: list[Linha]) -> None:
    """Compra e venda do mesmo ativo no dia: quantidades iguais = day trade; diferentes = conferir manualmente."""
    grupos: dict[tuple, list[Linha]] = defaultdict(list)
    for linha in linhas:
        if linha.tipo == "OPERACAO" and linha.evento in ("C", "V"):
            grupos[(linha.data, linha.ticker)].append(linha)
    for grupo in grupos.values():
        compras = sum(lin.quantidade for lin in grupo if lin.evento == "C")
        vendas = -sum(lin.quantidade for lin in grupo if lin.evento == "V")
        if not compras or not vendas:
            continue
        for lin in grupo:
            if compras == vendas:
                lin.daytrade = True
            elif lin.status == "novo":
                lin.status = "verificar"
                lin.motivo = "Compra e venda no mesmo dia com quantidades diferentes: confira a parte em day trade"


def analisar(sessao: Session, investidor_id: int, conteudo: bytes) -> Previa:
    relatorio, linhas = ler(conteudo)
    validas = [lin for lin in linhas if lin.tipo != "IGNORADA"]

    ocorrencias: dict[tuple, int] = defaultdict(int)
    for linha in validas:
        chave = (linha.relatorio, linha.data, linha.ticker, linha.evento, linha.quantidade, linha.preco, linha.valor)
        ocorrencias[chave] += 1
        linha.hash = _hash(investidor_id, linha, ocorrencias[chave])

    origens = (ORIGEM_B3, ORIGEM_PLANILHA_OPERACOES)
    hashes = set(sessao.scalars(select(Operacao.hash_origem).where(Operacao.origem.in_(origens))))
    hashes |= set(sessao.scalars(select(Provento.hash_origem).where(Provento.origem.in_(origens))))
    for linha in validas:
        if linha.hash in hashes:
            linha.status, linha.motivo = "duplicado", "Já importado anteriormente"

    _marcar_daytrade(validas)
    _comparar_existentes(sessao, investidor_id, validas)

    ativos = {a.ticker: a for a in sessao.scalars(select(Ativo).where(Ativo.ticker.in_({lin.ticker for lin in validas})))}
    corretoras = {_normalizar(c.nome).upper(): c for c in sessao.scalars(select(Corretora))}
    previa = Previa(relatorio, linhas)
    for linha in validas:
        if linha.status in ("novo", "verificar"):
            if linha.ticker not in ativos:
                previa.ativos_novos.setdefault(linha.ticker, linha.classe or "AÇÃO")
            if linha.instituicao:
                nome = _nome_corretora(linha.instituicao)
                if nome not in corretoras and nome not in previa.corretoras_novas:
                    previa.corretoras_novas.append(nome)
    return previa


def _comparar_existentes(sessao: Session, investidor_id: int, linhas: list[Linha]) -> None:
    """Compara a soma diária (por ativo e evento) do extrato com a do banco: igual = duplicado; diferente = verificar."""
    datas = [lin.data for lin in linhas if lin.data]
    if not datas:
        return
    inicio, fim = min(datas), max(datas)
    existentes_op: dict[tuple, Decimal] = defaultdict(Decimal)
    for ticker, dia, evento, qtd in sessao.execute(
        select(Ativo.ticker, Operacao.data, Operacao.evento, Operacao.quantidade)
        .join(Ativo, Ativo.id == Operacao.ativo_id)
        .where(Operacao.investidor_id == investidor_id, Operacao.data.between(inicio, fim))
    ):
        existentes_op[(ticker, dia, evento)] += abs(qtd)
    existentes_prov: dict[tuple, tuple[Decimal, Decimal]] = defaultdict(lambda: (Decimal(0), Decimal(0)))
    for ticker, dia, evento, valor, irrf in sessao.execute(
        select(Ativo.ticker, Provento.data_pagamento, Provento.evento, Provento.valor, Provento.irrf)
        .join(Ativo, Ativo.id == Provento.ativo_id)
        .where(Provento.investidor_id == investidor_id, Provento.data_pagamento.between(inicio, fim))
    ):
        bruto, liquido = existentes_prov[(ticker, dia, evento)]
        existentes_prov[(ticker, dia, evento)] = (bruto + valor, liquido + valor - irrf)

    grupos: dict[tuple, list[Linha]] = defaultdict(list)
    for linha in linhas:
        grupos[(linha.tipo, linha.ticker, linha.data, linha.evento)].append(linha)
    for (tipo, ticker, dia, evento), grupo in grupos.items():
        pendentes = [lin for lin in grupo if lin.status in ("novo", "verificar")]
        if not pendentes:
            continue
        if tipo == "OPERACAO":
            existente = existentes_op.get((ticker, dia, evento), Decimal(0))
            total = sum((abs(lin.quantidade) for lin in grupo), Decimal(0))
            igual = existente == total
        else:
            bruto, liquido = existentes_prov.get((ticker, dia, evento), (Decimal(0), Decimal(0)))
            existente = bruto
            total = sum((lin.valor for lin in grupo), Decimal(0))
            tolerancia = max(_TOLERANCIA_VALOR, total * Decimal("0.005"))
            igual = abs(bruto - total) <= tolerancia or abs(liquido - total) <= tolerancia
        if not existente:
            continue
        for linha in pendentes:
            if igual:
                linha.status, linha.motivo = "duplicado", "Já existe lançamento igual neste dia"
            else:
                linha.status = "verificar"
                linha.motivo = "Já existem lançamentos deste ativo e evento no dia com quantidade/valor diferente"


# ---------- Gravação ----------

@dataclass
class Resultado:
    operacoes: int = 0
    proventos: int = 0
    ativos_criados: list[str] = field(default_factory=list)
    corretoras_criadas: list[str] = field(default_factory=list)
    lote_id: int | None = None


def importar(
    sessao: Session, investidor_id: int, conteudo: bytes, incluir: set[int], arquivo: str | None = None
) -> Resultado:
    """Grava as linhas "novo" e as "verificar" cujo número está em `incluir`, num lote que pode ser desfeito."""
    if sessao.get(Investidor, investidor_id) is None:
        raise ExtratoInvalido("Investidor não encontrado")
    previa = analisar(sessao, investidor_id, conteudo)
    resultado = Resultado()
    ativos = {a.ticker: a for a in sessao.scalars(select(Ativo))}
    corretoras = {_normalizar(c.nome).upper(): c for c in sessao.scalars(select(Corretora))}
    lote: LoteImportacao | None = None

    def lote_id() -> int:
        nonlocal lote
        if lote is None:
            tipo_lote = "PLANILHA_OPERACOES" if previa.relatorio == "PLANILHA_OPERACOES" else "EXTRATO_B3"
            lote = lotes.novo(sessao, tipo_lote, investidor_id, arquivo)
        return lote.id

    def ativo(linha: Linha) -> Ativo:
        if linha.ticker not in ativos:
            novo = Ativo(
                ticker=linha.ticker, nome=linha.nome_produto, classe=previa.ativos_novos.get(linha.ticker, "AÇÃO"),
                moeda="BRL", mercado="BVMF", cotacao_automatica=True,
            )
            sessao.add(novo)
            ativos[linha.ticker] = novo
            resultado.ativos_criados.append(linha.ticker)
        return ativos[linha.ticker]

    def corretora(linha: Linha) -> Corretora | None:
        if not linha.instituicao:
            return None
        nome = _nome_corretora(linha.instituicao)
        if nome not in corretoras:
            corretoras[nome] = Corretora(nome=nome)
            sessao.add(corretoras[nome])
            resultado.corretoras_criadas.append(nome)
        return corretoras[nome]

    for linha in previa.linhas:
        if linha.status != "novo" and not (linha.status == "verificar" and linha.numero in incluir):
            continue
        if linha.tipo == "OPERACAO":
            observacao = (
                "Importado do extrato B3"
                if linha.origem == ORIGEM_B3
                else "Importado de planilha de operações"
            )
            if linha.evento_original and linha.evento_original != linha.evento:
                observacao += f" · sigla informada: {linha.evento_original}"
            sessao.add(Operacao(
                investidor_id=investidor_id, ativo=ativo(linha), corretora=corretora(linha), data=linha.data,
                evento=linha.evento, quantidade=linha.quantidade, preco=linha.preco, taxas=linha.taxas, irrf=linha.irrf,
                moeda=linha.moeda, cambio=Decimal(1), daytrade=linha.daytrade,
                observacao=observacao,
                origem=linha.origem,
                hash_origem=linha.hash, lote_id=lote_id(),
            ))
            resultado.operacoes += 1
        elif linha.tipo == "PROVENTO":
            sessao.add(Provento(
                investidor_id=investidor_id, ativo=ativo(linha), corretora=corretora(linha),
                data_pagamento=linha.data, evento=linha.evento, valor=linha.valor, irrf=Decimal(0), taxas=Decimal(0),
                moeda="BRL", cambio=Decimal(1), observacao="Importado do extrato B3", origem=linha.origem, hash_origem=linha.hash,
                lote_id=lote_id(),
            ))
            resultado.proventos += 1
    if lote is not None:
        lotes.contar(sessao, lote)
        resultado.lote_id = lote.id
    sessao.commit()
    return resultado
