from datetime import date, timedelta
from decimal import Decimal as D
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Ativo, Cotacao, Fundamento, Investidor, Operacao
from app.providers import fundamentus
from app.providers.base import CotacaoAtual
from app.services import valuation
from app.services.rentabilidade import fim_do_mes


def premissas_teste() -> dict[str, D | None]:
    return {
        "lpa": D("2"),
        "vpa": D("10"),
        "dividendo_anual": D("1.2"),
        "roe": D("0.15"),
        "payout": D("0.5"),
        "g": D("0.02"),
        "ke": D("0.10"),
        "pl_historico": D("10"),
        "pl_setor": D("12"),
        "fcfe_1": D("1"),
        "fcfe_2": D("2"),
        "fcfe_3": D("3"),
        "fcfe_4": D("4"),
        "fcfe_5": D("5"),
    }


def test_sete_modelos_calculam_precos_com_as_formulas_aprovadas():
    resultados = {item["id"]: item for item in valuation._modelos(premissas_teste())}

    assert len(resultados) == 7
    assert resultados["graham"]["preco_justo"] == (D("22.5") * D("2") * D("10")).sqrt()
    assert resultados["bazin"]["preco_justo"] == D("20")
    assert resultados["gordon"]["preco_justo"] == D("15.3")
    assert resultados["pl_historico"]["preco_justo"] == D("20")
    assert resultados["pl_setor"]["preco_justo"] == D("24")
    assert resultados["pvp_justificado"]["preco_justo"] == D("16.25")

    ke, g = D("0.10"), D("0.02")
    fluxos = [D("1"), D("2"), D("3"), D("4"), D("5")]
    esperado_dcf = sum((fcfe / (D(1) + ke) ** ano for ano, fcfe in enumerate(fluxos, 1)), D(0))
    esperado_dcf += fluxos[-1] * (D(1) + g) / (ke - g) / (D(1) + ke) ** 5
    assert abs(resultados["dcf_fcfe"]["preco_justo"] - esperado_dcf) < D("1e-20")


def test_modelos_que_nao_tem_premissas_validas_ficam_indisponiveis():
    premissas = premissas_teste()
    premissas.update({"ke": D("0.02"), "g": D("0.02"), "pl_historico": None, "pl_setor": None})

    resultados = {item["id"]: item for item in valuation._modelos(premissas)}

    assert resultados["dcf_fcfe"]["preco_justo"] is None
    assert resultados["gordon"]["preco_justo"] is None
    assert resultados["pvp_justificado"]["preco_justo"] is None
    assert resultados["pl_historico"]["preco_justo"] is None
    assert all(resultados[chave]["motivo"] for chave in ("dcf_fcfe", "gordon", "pvp_justificado", "pl_historico"))


def test_get_deriva_premissas_do_fundamentus_e_cotacao():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        ativo = Ativo(ticker="ABCD3", classe="AÇÃO", moeda="BRL")
        sessao.add(ativo)
        sessao.flush()
        hoje = date.today()
        sessao.add_all(
            [
                Cotacao(ativo_id=ativo.id, data=hoje, preco=D("100"), fonte="teste"),
                Fundamento(
                    ativo_id=ativo.id,
                    data_ref=hoje,
                    fonte="Fundamentus",
                    preco_lucro=D("10"),
                    preco_valor_patrimonial=D("2"),
                    dividend_yield=D("5"),
                    roe=D("15"),
                ),
            ]
        )

        resultado = valuation.consultar(sessao, ativo.id, None)

        assert resultado["premissas"]["lpa"] == D("10")
        assert resultado["premissas"]["vpa"] == D("50")
        assert resultado["premissas"]["dividendo_anual"] == D("5")
        assert resultado["premissas"]["roe"] == D("0.15")
        assert resultado["premissas"]["payout"] == D("0.5")
        assert resultado["premissas"]["g"] == D("0.075")
        assert resultado["premissas"]["ke"] is None
        assert resultado["fundamento_data"] == hoje
    engine.dispose()


def test_tir_e_twr_respeitam_ativo_e_filtro_de_investidores():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        ana = Investidor(nome="Ana")
        bia = Investidor(nome="Bia")
        ativo = Ativo(ticker="ABCD3", classe="AÇÃO", moeda="BRL")
        outro_ativo = Ativo(ticker="EFGH3", classe="AÇÃO", moeda="BRL")
        sessao.add_all([ana, bia, ativo, outro_ativo])
        sessao.flush()
        hoje = date.today()
        fim_anterior = fim_do_mes(hoje.replace(day=1) - timedelta(days=1))
        inicio = fim_anterior - timedelta(days=10)
        sessao.add_all(
            [
                Operacao(
                    investidor_id=ana.id, ativo_id=ativo.id, data=inicio, evento="C",
                    quantidade=D("10"), preco=D("100"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=bia.id, ativo_id=ativo.id, data=inicio, evento="C",
                    quantidade=D("100"), preco=D("10"), moeda="BRL", cambio=D("1"),
                ),
                Operacao(
                    investidor_id=ana.id, ativo_id=outro_ativo.id, data=inicio, evento="C",
                    quantidade=D("50"), preco=D("20"), moeda="BRL", cambio=D("1"),
                ),
                Cotacao(ativo_id=ativo.id, data=fim_anterior, preco=D("100"), fonte="teste"),
                Cotacao(ativo_id=ativo.id, data=hoje, preco=D("110"), fonte="teste"),
            ]
        )
        sessao.flush()

        resultado = valuation.consultar(sessao, ativo.id, [ana.id])

        assert len(resultado["rentabilidade"]["meses"]) == 2
        assert resultado["rentabilidade"]["meses"][0]["investido"] == D("1000")
        assert resultado["rentabilidade"]["meses"][-1]["mercado"] == D("1100")
        assert resultado["rentabilidade"]["meses"][-1]["twr"] == D("0.1")
        assert resultado["rentabilidade"]["tir_aa"] is not None
        assert resultado["rentabilidade"]["tir_am"] is not None
    engine.dispose()


def test_endpoint_salva_premissas_e_retorna_sete_modelos(cliente: TestClient):
    ativo = cliente.post("/api/ativos", json={"ticker": "ABCD3", "classe": "AÇÃO"}).json()
    rota = f"/api/valuation/{ativo['id']}"
    entrada = {campo: float(valor) if valor is not None else None for campo, valor in premissas_teste().items()}

    resposta = cliente.put(f"{rota}/premissas", json=entrada)

    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados["modelos"]) == 7
    assert dados["premissas"]["ke"] == 0.1
    assert dados["analise"]["modelos_disponiveis"] == 7
    assert dados["rentabilidade"]["meses"] == []

    recarregado = cliente.get(rota)
    assert recarregado.status_code == 200
    assert recarregado.json()["premissas"]["lpa"] == 2
    assert cliente.get("/api/valuation/99999").status_code == 404


def test_mediana_usa_apenas_modelos_calculaveis():
    assert valuation._mediana([D("10"), D("20"), D("30")]) == D("20")
    assert valuation._mediana([D("10"), D("20"), D("30"), D("40")]) == D("25")
    assert valuation._mediana([]) is None


def test_historico_mantem_ultimo_calculo_e_os_dois_anteriores(cliente: TestClient):
    ativo = cliente.post("/api/ativos", json={"ticker": "ABCD3", "classe": "AÇÃO"}).json()
    outro = cliente.post("/api/ativos", json={"ticker": "EFGH3", "classe": "AÇÃO"}).json()
    entrada = {campo: float(valor) if valor is not None else None for campo, valor in premissas_teste().items()}
    assert cliente.get("/api/valuation/historico").json() == []

    for bazin in (1, 2, 3, 4):
        dados = {**entrada, "dividendo_anual": bazin * 0.6, "fcfe_1": None}
        assert cliente.put(f"/api/valuation/{ativo['id']}/premissas", json=dados).status_code == 200
    cliente.put(f"/api/valuation/{outro['id']}/premissas", json=entrada)
    cliente.get(f"/api/valuation/{ativo['id']}")

    lista = cliente.get("/api/valuation/historico").json()

    assert {item["ticker"] for item in lista} == {"ABCD3", "EFGH3"}
    abcd = next(item for item in lista if item["ticker"] == "ABCD3")
    assert len(abcd["calculos"]) == 3
    assert [c["modelos"]["bazin"] for c in abcd["calculos"]] == [40, 30, 20]
    assert [c["premissas"]["dividendo_anual"] for c in abcd["calculos"]] == [2.4, 1.8, 1.2]
    assert abcd["calculos"][0]["modelos"]["dcf_fcfe"] is None
    assert abcd["calculos"][0]["modelos_disponiveis"] == 6
    assert abcd["calculos"][0]["preco_mediano"] is not None
    assert abcd["calculos"][0]["cotacao"] is None and abcd["upside_atual"] is None

    assert cliente.delete(f"/api/valuation/{ativo['id']}/historico").status_code == 204
    assert [item["ticker"] for item in cliente.get("/api/valuation/historico").json()] == ["EFGH3"]


def test_historico_calcula_upside_na_data_e_atual():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        ativo = Ativo(ticker="ABCD3", classe="AÇÃO", moeda="BRL")
        sessao.add(ativo)
        sessao.flush()
        hoje = date.today()
        sessao.add(Cotacao(ativo_id=ativo.id, data=hoje - timedelta(days=1), preco=D("10"), fonte="teste"))
        sessao.flush()
        premissas = {campo: None for campo in premissas_teste()}
        valuation.salvar_premissas(sessao, ativo.id, {**premissas, "dividendo_anual": D("1.2")}, None)
        sessao.add(Cotacao(ativo_id=ativo.id, data=hoje, preco=D("16"), fonte="teste"))
        sessao.commit()

        [item] = valuation.historico(sessao)

        assert item["calculos"][0]["preco_mediano"] == D("20")
        assert item["calculos"][0]["cotacao"] == D("10")
        assert item["calculos"][0]["upside"] == D("1")
        assert item["cotacao"] == D("16")
        assert item["upside_atual"] == D("0.25")
    engine.dispose()


class _ProvedorFalso:
    nome = "falso"

    def __init__(self, precos: dict[str, D]):
        self.precos = precos
        self.consultados: list[str] = []

    def cotacoes(self, ativos):
        self.consultados += [a.ticker for a in ativos]
        return {
            a.ticker: CotacaoAtual(a.ticker, self.precos[a.ticker], None, date.today(), "falso")
            for a in ativos
            if a.ticker in self.precos
        }

    def cambios(self, moedas):
        return {}


def test_preparar_ativo_cadastra_ticker_digitado_e_busca_cotacao_e_fundamentos(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        sessao.add(Ativo(ticker="OUTR3", classe="AÇÃO", moeda="BRL", mercado="BVMF"))
        sessao.commit()
        monkeypatch.setattr(
            fundamentus, "buscar_acoes",
            lambda _cliente: {"NOVO3": {"preco_lucro": D("10")}, "OUTR3": {"preco_lucro": D("5")}},
        )
        provedor = _ProvedorFalso({"NOVO3": D("20")})

        resultado = valuation.preparar_ativo(sessao, "NOVO3", "AÇÃO", [provedor], cliente_fundamentos=object())

        assert resultado["criado"] is True and resultado["avisos"] == []
        assert provedor.consultados == ["NOVO3"]
        detalhe = valuation.consultar(sessao, resultado["ativo_id"], None)
        assert detalhe["cotacao"] == D("20")
        assert detalhe["premissas"]["lpa"] == D("2")
        assert sessao.scalar(select(func.count()).select_from(Fundamento)) == 1

        repeticao = valuation.preparar_ativo(sessao, "NOVO3", "AÇÃO", [provedor], cliente_fundamentos=object())
        assert repeticao == {**resultado, "criado": False}
        assert provedor.consultados == ["NOVO3"]
    engine.dispose()


def test_preparar_ativo_avisa_quando_fontes_nao_encontram_o_ticker(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        monkeypatch.setattr(fundamentus, "buscar_acoes", lambda _cliente: {})

        resultado = valuation.preparar_ativo(sessao, "XPTO3", "AÇÃO", [_ProvedorFalso({})], object())

        assert resultado["criado"] is True
        assert len(resultado["avisos"]) == 2
        assert sessao.get(Ativo, resultado["ativo_id"]).ticker == "XPTO3"
    engine.dispose()


def test_endpoint_preparar_ativo_valida_ticker(cliente: TestClient):
    assert cliente.post("/api/valuation/ativo", json={"ticker": "a b"}).status_code == 422


def test_endpoint_buscar_premissas_atualiza_fontes_sem_salvar_por_cima_das_manuais(
    cliente: TestClient, monkeypatch
):
    ativo = cliente.post("/api/ativos", json={"ticker": "ABCD3", "classe": "AÇÃO"}).json()
    rota = f"/api/valuation/{ativo['id']}"
    entrada = {campo: None for campo in premissas_teste()}
    entrada.update({"lpa": 99, "ke": 0.1})
    assert cliente.put(f"{rota}/premissas", json=entrada).status_code == 200
    monkeypatch.setattr(valuation.cotacoes, "provedores_padrao", lambda: [_ProvedorFalso({"ABCD3": D("100")})])

    def atualizar_fundamentos(sessao, _cliente=None, hoje=None, ativo_ids=None):
        sessao.add(
            Fundamento(
                ativo_id=ativo["id"],
                data_ref=hoje or date.today(),
                fonte="teste",
                preco_lucro=D("10"),
                preco_valor_patrimonial=D("2"),
                dividend_yield=D("5"),
                roe=D("15"),
            )
        )
        sessao.commit()
        return SimpleNamespace(sem_dados=[], falhas=[])

    monkeypatch.setattr(valuation.fundamentos, "atualizar", atualizar_fundamentos)

    resposta = cliente.post(f"{rota}/buscar-premissas")

    assert resposta.status_code == 200
    assert resposta.json()["premissas"]["lpa"] == 10
    assert resposta.json()["premissas"]["vpa"] == 50
    assert resposta.json()["premissas"]["ke"] is None
    assert resposta.json()["avisos"] == []
    assert cliente.get(rota).json()["premissas"]["lpa"] == 99
