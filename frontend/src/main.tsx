import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Layout, PAGINAS } from "./components/Layout";
import { LimiteErro } from "./components/LimiteErro";
import { ProvedorInvestidor } from "./InvestidorContext";
import { Alocacao } from "./pages/Alocacao";
import { Aluguel } from "./pages/Aluguel";
import { Caixa } from "./pages/Caixa";
import { Conciliacao } from "./pages/Conciliacao";
import { Configuracoes } from "./pages/Configuracoes";
import { Cripto } from "./pages/Cripto";
import { EmConstrucao } from "./pages/EmConstrucao";
import { ImpostoRenda } from "./pages/ImpostoRenda";
import { Metas } from "./pages/Metas";
import { Operacoes } from "./pages/Operacoes";
import { Portfolio } from "./pages/Portfolio";
import { Proventos } from "./pages/Proventos";
import { Radar } from "./pages/Radar";
import { RendaFixa } from "./pages/RendaFixa";
import { Rentabilidade } from "./pages/Rentabilidade";
import { Relatorios } from "./pages/Relatorios";
import { Resumo } from "./pages/Resumo";
import { StatusAtivo } from "./pages/StatusAtivo";
import { Valuation } from "./pages/Valuation";
import { ValuationsSalvos } from "./pages/ValuationsSalvos";
import "./estilo.css";

const cliente = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 } },
});

const prontas: Record<string, JSX.Element> = {
  "/": <Resumo />,
  "/portfolio": <Portfolio />,
  "/dashboard": <Rentabilidade />,
  "/conciliacao": <Conciliacao />,
  "/operacoes": <Operacoes />,
  "/proventos": <Proventos />,
  "/aluguel": <Aluguel />,
  "/renda-fixa": <RendaFixa />,
  "/caixa": <Caixa />,
  "/relatorios": <Relatorios />,
  "/alocacao": <Alocacao />,
  "/metas": <Metas />,
  "/radar": <Radar />,
  "/ir": <ImpostoRenda />,
  "/status": <StatusAtivo />,
  "/novo-valuation": <Valuation />,
  "/meus-valuations": <ValuationsSalvos />,
  "/cripto": <Cripto />,
};

function RedirecionarValuation({ destino }: { destino: string }) {
  const { search, hash } = useLocation();
  return <Navigate to={`${destino}${search}${hash}`} replace />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LimiteErro>
      <QueryClientProvider client={cliente}>
        <ProvedorInvestidor>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/valuation" element={<RedirecionarValuation destino="/novo-valuation" />} />
                <Route path="/valuations-salvos" element={<RedirecionarValuation destino="/meus-valuations" />} />
                {PAGINAS.map((p) => (
                  <Route
                    key={p.caminho}
                    path={p.caminho}
                    element={<LimiteErro key={p.caminho}>{prontas[p.caminho] ?? <EmConstrucao titulo={p.rotulo} />}</LimiteErro>}
                  />
                ))}
                <Route
                  path="/configuracoes"
                  element={
                    <LimiteErro key="/configuracoes">
                      <Configuracoes />
                    </LimiteErro>
                  }
                />
                <Route path="*" element={<EmConstrucao titulo="Página não encontrada" />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ProvedorInvestidor>
      </QueryClientProvider>
    </LimiteErro>
  </StrictMode>,
);
