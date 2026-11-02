"""Modelos .xlsx para preencher e importar, no mesmo layout que os leitores de extrato reconhecem.

A 1ª aba é a que os leitores processam (só o cabeçalho, para o modelo nunca importar dados fictícios);
a 2ª traz as instruções, o significado de cada coluna e um exemplo preenchido.
"""

import io
from dataclasses import dataclass, field
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from ..dominio import EVENTOS_PLANILHA_CODIGOS

_LINHAS_FORMATADAS = 1000
_FORMATOS = {"data": "DD/MM/YYYY", "numero": "#,##0.########", "moeda": "#,##0.00"}
_CABECALHO = PatternFill("solid", fgColor="DBEAFE")


@dataclass(frozen=True)
class Coluna:
    titulo: str
    ajuda: str
    obrigatoria: bool = True
    formato: str | None = None  # data | numero | moeda
    opcoes: tuple[str, ...] = ()
    largura: int = 16


@dataclass(frozen=True)
class Modelo:
    arquivo: str
    aba: str
    descricao: str
    colunas: tuple[Coluna, ...]
    exemplo: tuple[tuple, ...]
    instrucoes: tuple[str, ...] = field(default=())


_INSTITUICAO = Coluna(
    "Instituição", "Nome da corretora; vira o cadastro de corretora no app", obrigatoria=False, largura=34,
)

MODELOS: dict[str, Modelo] = {
    "planilha-operacoes": Modelo(
        "modelo-planilha-operacoes.xlsx", "Operações",
        "Compras e vendas no layout simples de planilha do app.",
        (
            Coluna("ativo", "Ticker negociado (ex.: PETR4)", largura=14),
            Coluna("date", "Data da operação", formato="data", largura=14),
            Coluna(
                "evento", "Sigla do evento",
                opcoes=EVENTOS_PLANILHA_CODIGOS,
                largura=18,
            ),
            Coluna("qtd", "Quantidade conforme o evento", formato="numero", largura=12),
            Coluna("preco", "Preço unitário na moeda da operação (sinal conforme o evento)",
                   formato="moeda", largura=20),
            Coluna("taxas", "Corretagem e emolumentos, na moeda da operação", obrigatoria=False, formato="moeda", largura=12),
            Coluna("corretora", "Nome da corretora", obrigatoria=False, largura=20),
            Coluna("irrf", "IRRF da operação, na moeda da operação", obrigatoria=False, formato="moeda", largura=12),
            Coluna("moeda", "Moeda da operação", opcoes=("BRL", "USD", "EUR"), largura=12),
        ),
        (
            ("PETR4", date(2026, 3, 2), "C", 100, 38.5, 12.34, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 9), "V", 10, 40, 2.5, "XP", 0.01, "BRL"),
            ("O", date(2026, 3, 10), "C", 1, 200, 0, "XP", 0, "USD"),
            ("PETR4", date(2026, 3, 11), "DT", 2, 39, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 12), "IPO", 10, 10, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 13), "SUB", 10, 2, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 16), "BN", 5, 4.96, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 17), "S/I", 100, 0, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 18), "S/I", -100, 0, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 19), "DESDOBRAMENTO", 100, 0, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 20), "GRUPAMENTO", -100, 0, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 23), "TC", -10, 10, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 24), "AT", 10, 10, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 25), "AM", 10, -0.5, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 26), "CISAO", 10, -1, 0, "XP", 0, "BRL"),
            ("PETR4", date(2026, 3, 27), "V.SUB", -3, 2, 0, "XP", 0, "BRL"),
        ),
        (
            "Modelo personalizado para importar operações e eventos; preencha Evento com uma sigla válida da lista.",
            (
                "C, IPO, SUB, BN e CISAO usam quantidade positiva. V aceita quantidade negativa e é armazenada como saída; "
                "V.SUB aceita quantidade positiva ou negativa e é armazenada como saída. "
                "SUB deve informar no preço unitário o custo total por ativo, incluindo eventual custo do direito. "
                "BN mantém o preço informado para calcular o novo PM, sem somá-lo ao capital investido. DT usa quantidade positiva para compra e negativa "
                "para venda, marcando day trade."
            ),
            (
                "S/I aceita quantidade positiva para Desdobramento (Split) e negativa para Grupamento (Inplit).",
            ),
            (
                "DESDOBRAMENTO, GRUPAMENTO, TC e AT usam quantidade com sinal: positiva para entrada/aumento e "
                "negativa para saída/redução. Transferências devem ter as duas pontas em linhas separadas."
            ),
            (
                "AM exige quantidade positiva e preço unitário negativo. Eventos sem impacto de custo, como "
                "DESDOBRAMENTO/GRUPAMENTO, exigem preço zero. Taxas e IRRF devem ser não negativos."
            ),
            (
                "Informe a moeda da operação (BRL, USD ou EUR); os valores são importados na moeda informada. "
                "Proventos (DIVIDENDO, JSCP, RENDIMENTO, BTC/ALUGUEL, "
                "entre outros) devem ser importados pelo modelo de Proventos."
            ),
            (
                "BAIXA, R.CAP, EX.OPC, TERMO, AJ.POS, ISENTO, TAXA e C.COTA são reconhecidos como códigos "
                "documentados, mas não são suportados por este modelo; a linha será rejeitada com a justificativa."
            ),
        ),
    ),
    "b3-negociacao": Modelo(
        "modelo-b3-negociacao.xlsx", "Negociação",
        "Compras e vendas (mesmo layout do relatório Negociação da Área do Investidor da B3).",
        (
            Coluna("Data do Negócio", "Data do pregão", formato="data", largura=14),
            Coluna("Tipo de Movimentação", "Compra ou Venda", opcoes=("Compra", "Venda"), largura=20),
            Coluna(
                "Mercado", "Mercado à Vista, Mercado Fracionário ou Opção de Compra/Venda",
                opcoes=("Mercado à Vista", "Mercado Fracionário", "Opção de Compra", "Opção de Venda"), largura=22,
            ),
            Coluna("Prazo/Vencimento", "Vencimento da opção (não é usado na importação)", obrigatoria=False),
            _INSTITUICAO,
            Coluna(
                "Código de Negociação", "Ticker negociado; no fracionário o F final é removido (PETR4F → PETR4)",
                largura=20,
            ),
            Coluna("Quantidade", "Quantidade positiva, inclusive nas vendas", formato="numero", largura=12),
            Coluna("Preço", "Preço unitário em R$", formato="moeda", largura=12),
            Coluna(
                "Valor", "Quantidade × preço, em R$; se vazio, é calculado", obrigatoria=False, formato="moeda",
                largura=14,
            ),
        ),
        (
            (date(2026, 3, 2), "Compra", "Mercado à Vista", "-", "XP INVESTIMENTOS CCTVM S/A", "PETR4", 100, 38.5,
             3850),
            (date(2026, 3, 9), "Venda", "Mercado Fracionário", "-", "XP INVESTIMENTOS CCTVM S/A", "PETR4F", 10, 40,
             400),
        ),
        (
            "Compra e venda do mesmo ativo no mesmo dia e corretora são marcadas como day trade automaticamente.",
            "Termo, futuro e outros mercados não são importados: lance-os em Operações.",
        ),
    ),
    "b3-movimentacao": Modelo(
        "modelo-b3-movimentacao.xlsx", "Movimentação",
        "Proventos e eventos (mesmo layout do relatório Movimentação da Área do Investidor da B3).",
        (
            Coluna("Entrada/Saída", "Credito ou Debito (só créditos geram lançamento)", opcoes=("Credito", "Debito"),
                   largura=14),
            Coluna("Data", "Data do pagamento ou do evento", formato="data", largura=12),
            Coluna(
                "Movimentação", "Tipo do evento: Dividendo, Juros Sobre Capital Próprio, Rendimento, Reembolso, "
                "Amortização ou Desdobro (outros tipos são listados e ignorados)",
                opcoes=("Dividendo", "Juros Sobre Capital Próprio", "Rendimento", "Reembolso", "Amortização",
                        "Desdobro"),
                largura=28,
            ),
            Coluna("Produto", "Ticker - Nome do ativo (ex.: ITSA4 - ITAUSA S.A.)", largura=34),
            _INSTITUICAO,
            Coluna("Quantidade", "Quantidade de ativos no evento (no desdobro, a quantidade recebida)",
                   formato="numero", largura=12),
            Coluna("Preço unitário", "Valor por ativo, em R$", obrigatoria=False, formato="moeda", largura=14),
            Coluna("Valor da Operação", "Valor total recebido, em R$", formato="moeda", largura=18),
        ),
        (
            ("Credito", date(2026, 4, 1), "Dividendo", "ITSA4 - ITAUSA S.A.", "XP INVESTIMENTOS CCTVM S/A", 500,
             0.02, 10),
            ("Credito", date(2026, 4, 15), "Rendimento", "HGLG11 - CSHG LOGISTICA FII", "XP INVESTIMENTOS CCTVM S/A",
             20, 1.1, 22),
        ),
        ("Tesouro Direto e produtos sem código de negociação são ignorados.",),
    ),
    "b3-proventos": Modelo(
        "modelo-b3-proventos.xlsx", "Proventos recebidos",
        "Proventos já pagos (mesmo layout do relatório Proventos recebidos da Área do Investidor da B3).",
        (
            Coluna("Produto", "Ticker - Nome do ativo (ex.: ITSA4 - ITAUSA S.A.)", largura=34),
            Coluna("Pagamento", "Data do pagamento", formato="data", largura=12),
            Coluna(
                "Tipo de Evento", "Dividendo, Juros Sobre Capital Próprio, Rendimento ou Reembolso",
                opcoes=("Dividendo", "Juros Sobre Capital Próprio", "Rendimento", "Reembolso"), largura=28,
            ),
            _INSTITUICAO,
            Coluna("Quantidade", "Quantidade de ativos que geraram o provento", formato="numero", largura=12),
            Coluna("Preço unitário", "Valor por ativo, em R$", obrigatoria=False, formato="moeda", largura=14),
            Coluna("Valor líquido", "Valor recebido já descontado o IR, em R$", formato="moeda", largura=14),
        ),
        (
            ("ITSA4 - ITAUSA S.A.", date(2026, 4, 1), "Juros Sobre Capital Próprio", "XP INVESTIMENTOS CCTVM S/A",
             500, 0.017, 8.5),
        ),
    ),
    "aluguel": Modelo(
        "modelo-aluguel-btc.xlsx", "Extrato",
        "Aluguel de ações (BTC) no formato do extrato da corretora; também aceita .csv com as mesmas colunas.",
        (
            Coluna("Liquidação", "Data de liquidação", formato="data", largura=12),
            Coluna(
                "Lançamento", "Histórico iniciado por um dos textos reconhecidos, seguido do ticker (ver exemplo)",
                opcoes=("Crédito Ref. Taxa de Remuneração BTC", "DEBITO CBLC IRRF S/ RENDIMENTO DE BTC",
                        "Taxa de intermediação doador"),
                largura=52,
            ),
            Coluna("Ticker", "Ticker ou raiz (MGLU3 ou MGLU); se vazio, usa o ticker citado no lançamento",
                   obrigatoria=False, largura=10),
            Coluna("Valor", "Valor em R$ (o sinal é ignorado)", formato="moeda", largura=12),
        ),
        (
            (date(2026, 8, 5), "Crédito Ref. Taxa de Remuneração BTC MGLU", "MGLU", 23.24),
            (date(2026, 8, 5), "DEBITO CBLC IRRF S/ RENDIMENTO DE BTC MGLU", "MGLU", -5.22),
            (date(2026, 8, 5), "Taxa de intermediação doador MGLU3", "MGLU3", -11.99),
        ),
        (
            "Remuneração, IRRF e taxa da mesma data e ativo viram um único provento de aluguel.",
            "Linhas com outros históricos (TED, compras etc.) podem ficar no arquivo: são ignoradas.",
        ),
    ),
}


def _validacao(coluna: Coluna, letra: str) -> DataValidation:
    # Aviso em vez de bloqueio: a B3 usa variações de grafia que os leitores também aceitam.
    validacao = DataValidation(
        type="list", formula1='"' + ",".join(coluna.opcoes) + '"', allow_blank=True,
        showErrorMessage=True, errorStyle="warning", error="Valor fora da lista sugerida.",
    )
    validacao.add(f"{letra}2:{letra}{_LINHAS_FORMATADAS + 1}")
    return validacao


def _aba_dados(livro: Workbook, modelo: Modelo) -> None:
    planilha = livro.active
    planilha.title = modelo.aba
    for indice, coluna in enumerate(modelo.colunas, start=1):
        letra = get_column_letter(indice)
        celula = planilha.cell(row=1, column=indice, value=coluna.titulo)
        celula.font, celula.fill = Font(bold=True), _CABECALHO
        planilha.column_dimensions[letra].width = coluna.largura
        if coluna.formato:
            for linha in range(2, _LINHAS_FORMATADAS + 2):
                planilha.cell(row=linha, column=indice).number_format = _FORMATOS[coluna.formato]
        if coluna.opcoes:
            planilha.add_data_validation(_validacao(coluna, letra))
    planilha.freeze_panes = "A2"


def _aba_instrucoes(livro: Workbook, modelo: Modelo) -> None:
    planilha = livro.create_sheet("Instruções")
    negrito = Font(bold=True)
    planilha.append([modelo.descricao])
    planilha["A1"].font = Font(bold=True, size=12)
    planilha.append([])
    for texto in (
        f"Preencha a aba '{modelo.aba}' a partir da linha 2, sem alterar o cabeçalho nem a ordem das abas.",
        "Importe pelo botão de importação da tela: o app mostra uma prévia antes de gravar e não duplica "
        "lançamentos já existentes.",
        *modelo.instrucoes,
    ):
        planilha.append([f"• {texto}"])
    planilha.append([])
    planilha.append(["Coluna", "Obrigatória", "O que preencher"])
    for celula in planilha[planilha.max_row]:
        celula.font, celula.fill = negrito, _CABECALHO
    for coluna in modelo.colunas:
        planilha.append([coluna.titulo, "Sim" if coluna.obrigatoria else "Não", coluna.ajuda])
    planilha.append([])
    planilha.append(["Exemplo (não é importado)"])
    planilha.cell(row=planilha.max_row, column=1).font = negrito
    planilha.append([c.titulo for c in modelo.colunas])
    for celula in planilha[planilha.max_row]:
        celula.font, celula.fill = negrito, _CABECALHO
    for exemplo in modelo.exemplo:
        planilha.append(list(exemplo))
        for indice, coluna in enumerate(modelo.colunas, start=1):
            if coluna.formato:
                planilha.cell(row=planilha.max_row, column=indice).number_format = _FORMATOS[coluna.formato]
    planilha.column_dimensions["A"].width = 30
    planilha.column_dimensions["B"].width = 24
    planilha.column_dimensions["C"].width = 90
    for linha in planilha.iter_rows(min_col=3, max_col=3):
        linha[0].alignment = Alignment(wrap_text=True, vertical="top")


def gerar(nome: str) -> tuple[str, bytes]:
    """(nome do arquivo, conteúdo .xlsx) do modelo. KeyError se o modelo não existir."""
    modelo = MODELOS[nome]
    livro = Workbook()
    _aba_dados(livro, modelo)
    _aba_instrucoes(livro, modelo)
    saida = io.BytesIO()
    livro.save(saida)
    return modelo.arquivo, saida.getvalue()
