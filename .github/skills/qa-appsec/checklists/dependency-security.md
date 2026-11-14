# Segurança de dependências

## Inventário
- Manifestos e lockfiles cobrem dependências diretas/transitivas e plataformas relevantes?
- Versões, origem, licença, manutenção e compatibilidade são conhecidas?
- Bibliotecas abandonadas, duplicadas, privilegiadas ou não utilizadas foram identificadas?
- Atualizações críticas têm processo, responsável, validação e reversão?
- Componentes empacotados e dependências de Python portátil estão incluídos no inventário?

## Verificação segura
- Preferir inventário e advisories já disponíveis localmente.
- Antes de SCA externo, avaliar se nomes, versões ou arquivos serão transmitidos e obter autorização.
- Não instalar scanner nem executar atualização automática.
- Registrar ferramenta/versão, fonte dos dados, data, escopo e limites da cobertura.
- Diferenciar dependência declarada, presente no artefato, carregada em execução e alcançável.

## Resultado
Para CVE, confirmar pacote, faixa afetada, versão resolvida, condição de uso e mitigação. Não copiar
PoCs nem assumir impacto só pela presença de uma versão vulnerável.