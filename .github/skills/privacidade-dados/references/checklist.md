# Checklist — Privacidade de Dados

Cada item reprovado vira achado `PRIV-XXX` com evidência (`arquivo:linha`, caminho, tipo de arquivo,
saída de teste com dados fictícios) e proposta. Marque cada item como **OK · Achado · N/A · Não
verificado** (com motivo). Canais de vazamento genéricos:
[data-leakage-prevention](../../qa-appsec/checklists/data-leakage-prevention.md); segredos e proteção:
[secrets-and-data-protection](../../qa-appsec/checklists/secrets-and-data-protection.md).

> Escopo: práticas técnicas alinhadas aos princípios da LGPD. Processo jurídico/formal de
> conformidade está fora de escopo e não deve ser afirmado pelo relatório.

## 1. Inventário de dados
- [ ] Lista de campos pessoais/financeiros por entidade: identificadores (CPF/documentos), pessoais (nome, nascimento, contato), financeiros (posições, saldos, operações, rendimentos, patrimônio), de terceiros (familiares, dependentes, beneficiários).
- [ ] Para cada campo: finalidade, obrigatoriedade, origem (digitação, importação de planilha/extrato), local (tabela, arquivo, cache, `localStorage`), quem consome (telas, relatórios, exportações, jobs).
- [ ] Arquivos fora do banco catalogados: importações, anexos, exportações, relatórios gerados, backups, logs, caches.
- [ ] Inventário versionado em documentação (sem valores reais).

## 2. Minimização
- [ ] Só se coleta o necessário para a funcionalidade; campos opcionais são realmente opcionais.
- [ ] Importadores descartam colunas pessoais não usadas (não persistem o arquivo bruto inteiro sem necessidade).
- [ ] APIs devolvem apenas os campos usados pela tela (schemas de resposta específicos, não o modelo inteiro).
- [ ] Documento completo só onde é indispensável (ex.: declaração); listas usam forma mascarada.

## 3. Mascaramento
- [ ] Função/formatador único de mascaramento (ex.: `***.456.789-**`) reutilizado em UI, exportações, logs e erros.
- [ ] UI: documentos mascarados por padrão; "mostrar" é ação explícita do usuário, quando existir.
- [ ] Opção de ocultar valores (modo privacidade) avaliada para telas com patrimônio — **recomendação**, não imposição.
- [ ] Mensagens de erro e validação não ecoam documento/valores completos.
- [ ] Logs: ver `observabilidade-logs` (teste com `caplog`).
- [ ] Prints/screenshots de documentação e testes visuais usam somente dados fictícios.

## 4. Exportações, impressão, PDF e área de transferência
- [ ] Exportação com dados pessoais exibe aviso antes de gerar e indica o destino.
- [ ] Arquivo marcado (nome e/ou cabeçalho/rodapé "Contém dados pessoais — uso restrito").
- [ ] Destino padrão não é pasta sincronizada/compartilhada sem aviso; usuário escolhe o local.
- [ ] Exportação respeita o mascaramento quando o documento completo não é necessário.
- [ ] Metadados de PDF/XLSX não incluem nome de usuário do SO, caminhos locais ou dados extras.
- [ ] Cópia para área de transferência de dados sensíveis é ação explícita; não há cópia automática.
- [ ] CSS de impressão não revela dados ocultos na tela.

## 5. Exclusão e anonimização
- [ ] Existe operação para apagar uma pessoa/titular e **todos** os dados vinculados (operações, posições, proventos, metas, anexos, arquivos importados, caches).
- [ ] Integridade: `ON DELETE CASCADE`/lógica explícita sem órfãos; teste cria pessoa fictícia completa, apaga e verifica zero registros remanescentes.
- [ ] Alternativa de **anonimização** quando a exclusão quebrar agregados históricos (decisão do usuário, não da skill).
- [ ] Confirmação clara antes de apagar; ação registrada em log sem dados pessoais.
- [ ] Backups: limitação documentada (dado permanece em backups anteriores até expirarem pela retenção); orientação de expurgo/rotação.
- [ ] Exclusão não deixa dados no FTS/índices, cache em memória, `localStorage`/`IndexedDB` do front.
- [ ] SQLite: considerar `VACUUM` após exclusões relevantes (páginas livres guardam dados antigos) — avaliar impacto.

## 6. Dados em repouso
- [ ] Local do banco documentado, em diretório de dados do usuário, fora do repositório e preferencialmente fora de pastas sincronizadas (ou risco aceito explicitamente).
- [ ] Permissões do diretório restritas ao usuário.
- [ ] Recomendação de criptografia de disco do SO (BitLocker/FileVault/LUKS) documentada.
- [ ] Criptografia do banco (ex.: SQLCipher) apenas como **opção** avaliada, com impacto em backup/restauração.
- [ ] Backups e exportações automáticas com retenção definida e no mesmo nível de proteção do banco.
- [ ] Segredos da aplicação protegidos (ver checklist de segredos do `qa-appsec`).

## 7. Fixtures, seeds e dados de teste
- [ ] Fixtures, seeds, exemplos de documentação e dados de demo **somente fictícios**.
- [ ] Documentos fictícios gerados por algoritmo e identificáveis como fictícios; nomes genéricos.
- [ ] Nenhum extrato, planilha ou banco real em `tests/`, `fixtures/`, `docs/`, `samples/`.
- [ ] Cassetes de integrações sanitizados (ver `integracoes-externas`).
- [ ] Testes que geram arquivos usam diretório temporário isolado (`tmp_path`) e limpam ao final.

## 8. Higiene do repositório
- [ ] `.gitignore` cobre: bancos (`*.db`, `*.sqlite*`, `*-wal`, `*-shm`), planilhas/extratos (`*.xlsx`, `*.xls`, `*.csv` de dados, `*.pdf` de extratos), backups (`*.bak`, `*.zip` de backup, pasta de backups), `.env*` (exceto exemplo sem valores), logs, exportações, `qa-report/`.
- [ ] Verificar se algum desses arquivos **já está versionado** (`git ls-files` por extensão) e no histórico — sem abrir o conteúdo.
- [ ] Secret scanning disponível (pre-commit/CI: `gitleaks`, `detect-secrets` ou equivalente) — detalhes no `qa-appsec`.
- [ ] Artefatos de build/instalador não embutem banco, planilhas ou configuração local.

## 9. Envio a serviços externos
- [ ] Inventário do que sai em cada chamada externa: apenas identificadores públicos (tickers, códigos de índice, datas, termos de busca) — **nunca** nome, documento, quantidades, valores ou patrimônio.
- [ ] Teste com mock captura URL, query, headers e corpo e afirma ausência de PII/valores.
- [ ] Headers (`User-Agent`, `Referer`) sem nome de usuário do SO ou caminhos locais.
- [ ] Bibliotecas de terceiros não enviam telemetria implícita (verificar configurações/variáveis para desligar).
- [ ] Front: sem fontes, scripts ou analytics de CDN externa que vazem uso, quando a aplicação é local (ou risco documentado).

## 10. Temporários e retenção
- [ ] Uploads/importações processados e **removidos** (inclusive em caso de erro: `try/finally`, `TemporaryDirectory`).
- [ ] Diretório temporário próprio da aplicação, com limpeza no startup de resíduos antigos.
- [ ] Retenção definida para exportações automáticas, relatórios gerados, logs e backups.
- [ ] Cache do navegador/`localStorage` não guarda dados pessoais além do necessário.

## 11. Telemetria e relatórios de erro
- [ ] Nenhuma telemetria/relato de erro externo habilitado por padrão; somente **opt-in** explícito e reversível.
- [ ] Quando habilitada: conteúdo documentado, sem dados pessoais/financeiros, com mascaramento antes do envio.
- [ ] Pacote de diagnóstico local sem dados pessoais (ver `observabilidade-logs`).

## Exemplo de teste (Python, dados fictícios)

```python
def test_exclusao_remove_dados_vinculados(sessao, fabrica):
    pessoa = fabrica.pessoa(nome="Pessoa Ficticia", documento=gerar_cpf_ficticio())
    fabrica.operacoes(pessoa, n=3); fabrica.anexo(pessoa)
    servico.excluir_pessoa(sessao, pessoa.id)
    for modelo in MODELOS_VINCULADOS_A_PESSOA:
        assert sessao.query(modelo).filter_by(pessoa_id=pessoa.id).count() == 0

def test_provedor_nao_envia_dados_pessoais(respx_mock, carteira_ficticia):
    rota = respx_mock.get(url__regex=r".*").respond(json={})
    atualizar_cotacoes(carteira_ficticia)
    for chamada in rota.calls:
        texto = str(chamada.request.url) + chamada.request.content.decode(errors="ignore")
        assert carteira_ficticia.documento not in texto
        assert carteira_ficticia.nome not in texto
```
Exemplo ilustrativo: nomes de modelos, fábricas e serviços são do projeto auditado.
