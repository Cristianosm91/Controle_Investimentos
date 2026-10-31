import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout, PAGINAS } from "./components/Layout";
import { ProvedorInvestidor } from "./InvestidorContext";
import { Configuracoes } from "./pages/Configuracoes";
import { EmConstrucao } from "./pages/EmConstrucao";
import { Operacoes } from "./pages/Operacoes";
import { Portfolio } from "./pages/Portfolio";
import { Proventos } from "./pages/Proventos";
import "./estilo.css";

const cliente = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 } },
});

const prontas: Record<string, JSX.Element> = {
  "/portfolio": <Portfolio />,
  "/operacoes": <Operacoes />,
  "/proventos": <Proventos />,
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
                  element={prontas[p.caminho] ?? <EmConstrucao titulo={p.rotulo} fase={"fase" in p ? p.fase : undefined} />}
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
