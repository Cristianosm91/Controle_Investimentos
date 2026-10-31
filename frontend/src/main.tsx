import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout, PAGINAS } from "./components/Layout";
import { ProvedorInvestidor } from "./InvestidorContext";
import { Alocacao } from "./pages/Alocacao";
import { Aluguel } from "./pages/Aluguel";
import { Caixa } from "./pages/Caixa";
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
  "/operacoes": <Operacoes />,
  "/proventos": <Proventos />,
  "/aluguel": <Aluguel />,
  "/renda-fixa": <RendaFixa />,
  "/caixa": <Caixa />,
  "/alocacao": <Alocacao />,
  "/metas": <Metas />,
  "/radar": <Radar />,
  "/ir": <ImpostoRenda />,
  "/status": <StatusAtivo />,
  "/valuation": <Valuation />,
  "/valuations-salvos": <ValuationsSalvos />,
  "/cripto": <Cripto />,
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <ProvedorInvestidor>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              {PAGINAS.map((p) => (
                <Route
                  key={p.caminho}
                  path={p.caminho}
                  element={prontas[p.caminho] ?? <EmConstrucao titulo={p.rotulo} />}
                />
              ))}
              <Route path="/configuracoes" element={<Configuracoes />} />
              <Route path="*" element={<EmConstrucao titulo="Página não encontrada" />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ProvedorInvestidor>
    </QueryClientProvider>
  </StrictMode>,
);
